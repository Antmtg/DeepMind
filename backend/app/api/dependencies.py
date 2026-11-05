import secrets
from collections.abc import Callable

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.device import Device
from app.models.user import User, UserRole
from app.services.audit_service import register_event
from app.services.device_service import authenticate_device


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    biomonitor_access: str | None = Cookie(default=None),
) -> User:
    """Acepta cookie HttpOnly del navegador o Bearer token para pruebas de API."""
    token = biomonitor_access
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Debes iniciar sesión")

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión es inválida o venció",
        ) from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no disponible")
    return user


def require_roles(*allowed_roles: UserRole) -> Callable:
    """Fábrica de dependencias RBAC: autenticado no significa autorizado."""
    allowed_values = {role.value for role in allowed_roles}

    def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.role not in allowed_values:
            register_event(
                db,
                action="ACCESS_DENIED",
                status="DENIED",
                detail=f"Rol {current_user.role} sin permiso para {request.method} {request.url.path}",
                user_id=current_user.id,
                email_attempted=current_user.email,
                ip_address=request.client.host if request.client else None,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu rol no tiene permiso para esta operación",
            )
        return current_user

    return role_checker


def get_current_device(
    request: Request,
    x_device_api_key: str | None = Header(default=None, alias="X-Device-Api-Key"),
    db: Session = Depends(get_db),
) -> Device:
    """Autentica un ESP32 y audita cualquier intento rechazado.

    La clave nunca se guarda en el detalle de auditoría: solo se registra la
    ruta, el motivo y la IP de origen.
    """
    ip_address = request.client.host if request.client else None
    if not x_device_api_key:
        register_event(
            db,
            action="DEVICE_AUTH_FAILED",
            status="DENIED",
            detail=f"Falta X-Device-Api-Key en {request.method} {request.url.path}",
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta la clave del dispositivo (header X-Device-Api-Key)",
        )
    try:
        return authenticate_device(db, x_device_api_key)
    except HTTPException as error:
        register_event(
            db,
            action="DEVICE_AUTH_FAILED",
            status="DENIED",
            detail=(
                f"Credencial de dispositivo rechazada en "
                f"{request.method} {request.url.path}: {error.detail}"
            ),
            ip_address=ip_address,
        )
        raise


def require_provisioning_key(
    x_provisioning_key: str | None = Header(
        default=None, alias="X-Provisioning-Key"
    ),
) -> None:
    """Protege el endpoint que usan los ESP32 para pedir un código.

    La clave es compartida por los pocos dispositivos del servidor casero y se
    configura en ``DEVICE_PROVISIONING_KEY``. No se usa la sesión de usuario
    porque el hardware no tiene cookies ni JWT.
    """
    settings = get_settings()
    expected = settings.device_provisioning_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El aprovisionamiento de dispositivos está desactivado",
        )
    if not x_provisioning_key or not secrets.compare_digest(
        x_provisioning_key, expected
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave de aprovisionamiento inválida",
        )

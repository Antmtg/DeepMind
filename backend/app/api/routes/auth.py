from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, MessageResponse
from app.schemas.user import UserPublic
from app.services.audit_service import register_event
from app.services.auth_service import authenticate_user
from app.core.security import hash_password, verify_password
from app.services.user_service import validar_password


router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.email, data.password)
    client_ip = request.client.host if request.client else None

    if user is None:
        register_event(
            db,
            action="LOGIN",
            status="DENIED",
            detail="Credenciales incorrectas o cuenta inactiva",
            email_attempted=data.email.lower(),
            ip_address=client_ip,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    settings = get_settings()
    token = create_access_token(user.id, user.role)
    response.set_cookie(
        key="biomonitor_access",
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    register_event(
        db,
        action="LOGIN",
        status="SUCCESS",
        detail=f"Inicio de sesión como {user.role}",
        user_id=user.id,
        email_attempted=user.email,
        ip_address=client_ip,
    )
    return LoginResponse(
        message="Inicio de sesión correcto",
        user=UserPublic.model_validate(user),
        expires_in_minutes=settings.access_token_expire_minutes,
    )


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cambio de contraseña por la propia usuaria.

    Cada persona entra la primera vez con la contraseña primaria que le
    asignamos en persona y la reemplaza por una propia aquí.
    """
    if not verify_password(data.current_password, current_user.password_hash):
        register_event(
            db,
            action="PASSWORD_CHANGED",
            status="DENIED",
            detail="La contraseña actual no coincide",
            user_id=current_user.id,
            email_attempted=current_user.email,
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La contraseña actual no coincide",
        )

    validar_password(data.new_password, current_user.email)
    if verify_password(data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La contraseña nueva es igual a la actual",
        )

    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    register_event(
        db,
        action="PASSWORD_CHANGED",
        status="SUCCESS",
        detail="La usuaria actualizó su contraseña",
        user_id=current_user.id,
        email_attempted=current_user.email,
        ip_address=request.client.host if request.client else None,
    )
    return MessageResponse(message="Tu contraseña se actualizó")


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response.delete_cookie("biomonitor_access", path="/")
    register_event(
        db,
        action="LOGOUT",
        status="SUCCESS",
        detail="Cierre de sesión",
        user_id=current_user.id,
        email_attempted=current_user.email,
        ip_address=request.client.host if request.client else None,
    )
    return MessageResponse(message="Sesión cerrada")


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    return current_user

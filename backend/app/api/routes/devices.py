from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_device,
    get_current_user,
    require_provisioning_key,
    require_roles,
)
from app.core.config import get_settings
from app.core.rate_limit import allow_attempt, reset_attempts
from app.database.session import get_db
from app.models.device import Device
from app.models.user import User, UserRole
from app.schemas.device import (
    DeviceCapacity,
    DeviceCreate,
    DeviceCredentials,
    DeviceHeartbeat,
    DeviceKeyRotated,
    DeviceLatestMeasurement,
    DeviceMeasurementIngest,
    DevicePairRequest,
    DeviceProvisionRequest,
    DeviceProvisioned,
    DevicePublic,
    DeviceSelfRegisterRequest,
    DeviceUpdate,
)
from app.schemas.measurement import MeasurementPublic
from app.services.audit_service import register_event
from app.services.device_service import (
    count_devices,
    create_device,
    delete_device,
    device_capacity as get_device_capacity,
    get_device_for_user,
    heartbeat,
    latest_measurement_of_device,
    list_devices,
    measurements_of_device,
    pair_device,
    provision_device,
    register_device_for_user,
    rotate_api_key,
    unpair_device,
    update_device,
)
from app.services.measurement_service import create_measurement
# temperature removed

router = APIRouter(prefix="/devices", tags=["Dispositivos"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=list[DevicePublic])
def list_all_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista los dispositivos visibles según el rol y las asignaciones activas."""
    return list_devices(db, current_user)


@router.post(
    "/self-register",
    response_model=DeviceCredentials,
    status_code=status.HTTP_201_CREATED,
)
def self_register_device(
    data: DeviceSelfRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registro manual desde la app.

    Devuelve ``device_id`` y ``api_key`` una sola vez para grabarlos en el
    firmware. El dispositivo queda vinculado de inmediato a la cuenta actual.
    """
    device, api_key = register_device_for_user(db, current_user, data)
    register_event(
        db,
        action="DEVICE_REGISTERED",
        status="SUCCESS",
        detail=f"Registro manual del dispositivo {device.device_id}",
        user_id=current_user.id,
        email_attempted=current_user.email,
        ip_address=_client_ip(request),
    )
    return DeviceCredentials(
        device=DevicePublic.model_validate(device),
        api_key=api_key,
        message=(
            "Guarda la api_key ahora: no se volverá a mostrar. "
            "Cópiala en el firmware junto con el device_id."
        ),
    )


@router.post(
    "/provision",
    response_model=DeviceProvisioned,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_provisioning_key)],
)
def provision_esp32(
    data: DeviceProvisionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Aprovisiona un ESP32 y devuelve un código temporal de emparejamiento.

    Lo llama el hardware con el header ``X-Provisioning-Key``. El ESP32 debe
    mostrar el código por el monitor serial para que el usuario lo ingrese en
    la app.
    """
    settings = get_settings()
    device, pairing_code, api_key = provision_device(db, data)
    register_event(
        db,
        action="DEVICE_PROVISIONED",
        status="SUCCESS",
        detail=f"Aprovisionamiento del dispositivo {device.device_id}",
        ip_address=_client_ip(request),
    )
    return DeviceProvisioned(
        device_id=device.device_id,
        api_key=api_key,
        pairing_code=pairing_code,
        pairing_expires_at=device.pairing_expires_at,
        max_devices=settings.max_devices,
        registered_devices=count_devices(db),
        message=(
            f"Código válido por {settings.pairing_code_ttl_minutes} minutos. "
            "Ingrésalo en BioMonitor para vincular el sensor."
        ),
    )


@router.post("/pair", response_model=DevicePublic)
def pair_esp32(
    data: DevicePairRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vincula a la cuenta actual el dispositivo dueño del código."""
    settings = get_settings()
    attempt_key = f"pair:{current_user.id}"
    if not allow_attempt(
        attempt_key,
        limit=settings.pairing_max_attempts,
        window_seconds=settings.pairing_attempt_window_seconds,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera un minuto y vuelve a probar.",
        )

    try:
        device = pair_device(db, current_user, data.pairing_code)
    except HTTPException as error:
        register_event(
            db,
            action="DEVICE_PAIR_FAILED",
            status="DENIED",
            detail=f"Emparejamiento fallido: {error.detail}",
            user_id=current_user.id,
            email_attempted=current_user.email,
            ip_address=_client_ip(request),
        )
        raise

    reset_attempts(attempt_key)
    register_event(
        db,
        action="DEVICE_PAIRED",
        status="SUCCESS",
        detail=f"Dispositivo {device.device_id} vinculado a la cuenta",
        user_id=current_user.id,
        email_attempted=current_user.email,
        ip_address=_client_ip(request),
    )
    return DevicePublic.model_validate(device)


@router.get("/capacity", response_model=DeviceCapacity)
def capacity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Capacidad total del servidor y del usuario actual."""
    return get_device_capacity(db, current_user)


@router.post(
    "",
    response_model=DevicePublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def register_device(
    data: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registro administrativo con api_key explícita."""
    return create_device(db, data)


@router.get("/{device_id}", response_model=DevicePublic)
def get_one_device(
    device_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_device_for_user(db, device_id, current_user)


@router.patch("/{device_id}", response_model=DevicePublic)
def update_one_device(
    device_id: int = Path(ge=1),
    data: DeviceUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """El administrador edita todo; el propietario solo nombre y ubicación."""
    device = update_device(db, device_id, data, current_user)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )
    return device


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def remove_device(
    device_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_device(db, device_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )
    return None


@router.post("/{device_id}/rotate-key", response_model=DeviceKeyRotated)
def rotate_device_key(
    request: Request,
    device_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera una api_key nueva para el propietario o el administrador."""
    device, api_key = rotate_api_key(db, device_id, current_user)
    register_event(
        db,
        action="DEVICE_KEY_ROTATED",
        status="SUCCESS",
        detail=f"api_key rotada para el dispositivo {device.device_id}",
        user_id=current_user.id,
        email_attempted=current_user.email,
        ip_address=_client_ip(request),
    )
    return DeviceKeyRotated(
        device_id=device.device_id,
        api_key=api_key,
        message=(
            "Guarda la nueva api_key ahora: no se volverá a mostrar. "
            "Actualiza el firmware del ESP32."
        ),
    )


@router.post("/{device_id}/unpair", status_code=status.HTTP_204_NO_CONTENT)
def unpair_esp32(
    request: Request,
    device_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Desvincula el dispositivo sin borrar su historial de mediciones."""
    device = unpair_device(db, device_id, current_user)
    register_event(
        db,
        action="DEVICE_UNPAIRED",
        status="SUCCESS",
        detail=f"Dispositivo {device.device_id} desvinculado de la cuenta",
        user_id=current_user.id,
        email_attempted=current_user.email,
        ip_address=_client_ip(request),
    )
    return None


@router.get(
    "/{device_id}/measurements",
    response_model=list[MeasurementPublic],
)
def device_measurements(
    device_id: int = Path(ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(db, device_id, current_user)
    return measurements_of_device(db, device, limit=limit)


@router.get(
    "/{device_id}/latest-measurement",
    response_model=DeviceLatestMeasurement,
    tags=["Dispositivos"],
)
def device_latest_measurement(
    device_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Última medición de un dispositivo, solo si el usuario tiene acceso."""
    device = get_device_for_user(db, device_id, current_user)
    measurement = latest_measurement_of_device(db, device)
    if measurement is None:
        return DeviceLatestMeasurement(device_id=device.device_id)
    return DeviceLatestMeasurement(
        device_id=device.device_id,
        spo2=measurement.spo2,
        heart_rate_bpm=measurement.heart_rate_bpm,
        source=measurement.source,
        taken_at=measurement.measured_at,
    )


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
def ingest_measurement(
    request: Request,
    data: DeviceMeasurementIngest,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    """Recibe una lectura autenticada por la credencial del ESP32.

    El propietario se obtiene de ``device.user_id``; nunca del cuerpo del
    mensaje. Un dispositivo sin vincular no puede escribir historial.
    """
    if device.user_id is None:
        register_event(
            db,
            action="DEVICE_DATA_REJECTED",
            status="DENIED",
            detail=(
                f"Ingesta rechazada: el dispositivo {device.device_id} no está "
                "vinculado a una cuenta"
            ),
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El dispositivo aún no está vinculado a una cuenta",
        )
    if device.user is not None and not device.user.is_active:
        register_event(
            db,
            action="DEVICE_DATA_REJECTED",
            status="DENIED",
            detail=(
                f"Ingesta rechazada: la cuenta del dispositivo "
                f"{device.device_id} está inactiva"
            ),
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta propietaria del dispositivo está inactiva",
        )

    measurement = create_measurement(db, data, current_user=None, device=device)
    return {
        "id": measurement.id,
        "device_id": device.device_id,
        "spo2": measurement.spo2,
        "heart_rate_bpm": measurement.heart_rate_bpm,
        "measured_at": measurement.measured_at,
    }


@router.post("/heartbeat", response_model=DeviceHeartbeat)
def device_heartbeat_simple(
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    """Heartbeat sin id en la URL; el ESP32 solo envía su api_key."""
    return heartbeat(db, device)


@router.post("/{device_id}/heartbeat", response_model=DeviceHeartbeat)
def device_heartbeat(
    device_id: int = Path(ge=1),
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    if device.id != device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El dispositivo no coincide con la clave",
        )
    return heartbeat(db, device)

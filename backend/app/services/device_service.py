import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.device_keys import hash_device_key
from app.core.time import as_local
from app.models.assignment import CareAssignment
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.user import User, UserRole
from app.schemas.device import (
    DeviceCapacity,
    DeviceCreate,
    DeviceProvisionRequest,
    DeviceSelfRegisterRequest,
    DeviceUpdate,
)


def _now() -> datetime:
    """Hora local consciente de zona, coherente con ``Device.created_at``."""
    return datetime.now().astimezone()


def _normalize_mac(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def _normalize_pairing_code(value: str) -> str:
    """Acepta ``123456`` o ``123 456`` y devuelve solo los dígitos."""
    return "".join(character for character in value if character.isdigit())


def _hash_pairing_code(code: str) -> str:
    """Guarda un hash con la clave secreta; el código nunca queda en claro."""
    settings = get_settings()
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _generate_pairing_code(db: Session) -> tuple[str, str]:
    for _ in range(20):
        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = _hash_pairing_code(code)
        existing = db.scalar(
            select(Device.id).where(Device.pairing_code_hash == code_hash)
        )
        if existing is None:
            return code, code_hash
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="No se pudo generar un código de emparejamiento",
    )


def _generate_device_id(db: Session) -> str:
    for _ in range(20):
        candidate = f"ESP32-{secrets.token_hex(4).upper()}"
        if get_device_by_device_id(db, candidate) is None:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="No se pudo generar un identificador de dispositivo",
    )


def _generate_api_key() -> str:
    # 32 bytes aleatorios -> 43 caracteres URL-safe; cabe en String(64).
    return secrets.token_urlsafe(32)


def _get_by_api_key(db: Session, api_key: str) -> Device | None:
    stored_hash = hash_device_key(api_key)
    return db.scalar(select(Device).where(Device.api_key == stored_hash))


def authenticate_device(db: Session, api_key: str) -> Device:
    """Valida la api_key de un ESP32 y devuelve el dispositivo si está activo."""
    device = _get_by_api_key(db, api_key)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave de dispositivo inválida",
        )
    if not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El dispositivo está desactivado",
        )
    return device


def _assigned_patient_ids(db: Session, member: User) -> list[int]:
    return list(
        db.scalars(
            select(CareAssignment.patient_id).where(
                CareAssignment.member_id == member.id,
                CareAssignment.is_active.is_(True),
            )
        ).all()
    )


def count_devices(db: Session) -> int:
    return int(db.scalar(select(func.count(Device.id))) or 0)


def _count_user_devices(db: Session, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(Device.id)).where(Device.user_id == user_id)
        )
        or 0
    )


def _ensure_global_capacity(
    db: Session,
    *,
    additional: int = 1,
    exclude_device_id: int | None = None,
) -> None:
    settings = get_settings()
    stmt = select(func.count(Device.id))
    if exclude_device_id is not None:
        stmt = stmt.where(Device.id != exclude_device_id)
    current = int(db.scalar(stmt) or 0)
    if current + additional > settings.max_devices:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El servidor alcanzó el máximo de {settings.max_devices} "
                "dispositivos"
            ),
        )


def _ensure_user_capacity(
    db: Session,
    user_id: int,
    *,
    exclude_device_id: int | None = None,
) -> None:
    settings = get_settings()
    stmt = select(func.count(Device.id)).where(Device.user_id == user_id)
    if exclude_device_id is not None:
        stmt = stmt.where(Device.id != exclude_device_id)
    current = int(db.scalar(stmt) or 0)
    if current >= settings.max_devices_per_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cada cuenta puede tener "
                f"{settings.max_devices_per_user} dispositivo(s) vinculado(s)"
            ),
        )


def _ensure_device_id_available(
    db: Session,
    device_id: str,
    *,
    exclude_device_id: int | None = None,
) -> None:
    device = get_device_by_device_id(db, device_id)
    if device is not None and device.id != exclude_device_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un dispositivo con el id {device_id}",
        )


def _ensure_mac_available(
    db: Session,
    mac_address: str | None,
    *,
    exclude_device_id: int | None = None,
) -> None:
    if mac_address is None:
        return
    device = db.scalar(select(Device).where(Device.mac_address == mac_address))
    if device is not None and device.id != exclude_device_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un dispositivo con esa dirección MAC",
        )


def _commit_device(db: Session, device: Device) -> Device:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El device_id o la dirección MAC ya están registrados",
        ) from None
    db.refresh(device)
    return device


def list_devices(db: Session, current_user: User | None = None) -> list[Device]:
    """Lista los dispositivos visibles para el usuario según su rol.

    - Paciente: solo los dispositivos de su propiedad.
    - Cuidador/especialista: los propios y los de sus pacientes asignados.
    - Administrador/auditor: todos.
    """
    stmt = (
        select(Device)
        .options(joinedload(Device.user))
        .order_by(Device.created_at)
    )
    if current_user is not None:
        if current_user.role == UserRole.ATHLETE.value:
            stmt = stmt.where(Device.user_id == current_user.id)
        elif current_user.role == UserRole.COACH.value:
            patient_ids = _assigned_patient_ids(db, current_user)
            if patient_ids:
                stmt = stmt.where(
                    or_(
                        Device.user_id == current_user.id,
                        Device.user_id.in_(patient_ids),
                    )
                )
            else:
                stmt = stmt.where(Device.user_id == current_user.id)
    return db.scalars(stmt).all()


def get_device(db: Session, device_id: int) -> Device | None:
    return db.scalar(
        select(Device)
        .options(joinedload(Device.user))
        .where(Device.id == device_id)
    )


def get_device_by_device_id(db: Session, device_id: str) -> Device | None:
    return db.scalar(select(Device).where(Device.device_id == device_id))


def can_access_device(db: Session, device: Device, user: User) -> bool:
    if user.role == UserRole.ADMIN.value:
        return True
    # Cualquier rol puede acceder a un dispositivo propio (auto-vinculo).
    if device.user_id == user.id:
        return True
    if user.role == UserRole.COACH.value:
        if device.user_id is None:
            return False
        assignment = db.scalar(
            select(CareAssignment.id).where(
                CareAssignment.patient_id == device.user_id,
                CareAssignment.member_id == user.id,
                CareAssignment.is_active.is_(True),
            )
        )
        return assignment is not None
    return False


def get_device_for_user(db: Session, device_id: int, user: User) -> Device:
    device = get_device(db, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )
    if not can_access_device(db, device, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este dispositivo",
        )
    return device


def _validate_owner(db: Session, user_id: int | None) -> None:
    if user_id is None:
        return
    owner = db.get(User, user_id)
    if owner is None or owner.role != UserRole.ATHLETE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El propietario debe ser un paciente existente",
        )


def create_device(db: Session, data: DeviceCreate) -> Device:
    """Registro administrativo clásico (permite asignar propietario)."""
    _ensure_global_capacity(db)
    _ensure_device_id_available(db, data.device_id)
    _ensure_mac_available(db, data.mac_address)
    _validate_owner(db, data.user_id)
    if data.user_id is not None:
        _ensure_user_capacity(db, data.user_id)
    payload = data.model_dump()
    payload["api_key"] = hash_device_key(payload["api_key"])
    device = Device(**payload)
    db.add(device)
    return _commit_device(db, device)


def update_device(
    db: Session,
    device_id: int,
    data: DeviceUpdate,
    current_user: User,
) -> Device | None:
    device = get_device(db, device_id)
    if device is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for required_field in ("name", "api_key", "is_active"):
        if required_field in update_data and update_data[required_field] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El campo {required_field} no puede ser nulo",
            )

    is_admin = current_user.role == UserRole.ADMIN.value
    is_owner = device.user_id is not None and device.user_id == current_user.id

    if not is_admin:
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes editar este dispositivo",
            )
        # El propietario solo puede personalizar nombre y ubicación.
        forbidden = set(update_data) - {"name", "location"}
        if forbidden:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Solo puedes cambiar el nombre y la ubicación de tu "
                    "dispositivo"
                ),
            )

    if "user_id" in update_data:
        _validate_owner(db, update_data["user_id"])
        if update_data["user_id"] is not None:
            _ensure_user_capacity(
                db,
                update_data["user_id"],
                exclude_device_id=device.id,
            )
    if "mac_address" in update_data:
        _ensure_mac_available(
            db,
            update_data["mac_address"],
            exclude_device_id=device.id,
        )
    if "api_key" in update_data:
        update_data["api_key"] = hash_device_key(update_data["api_key"])

    for field, value in update_data.items():
        setattr(device, field, value)
    db.add(device)
    return _commit_device(db, device)


def delete_device(db: Session, device_id: int) -> bool:
    device = get_device(db, device_id)
    if device is None:
        return False
    db.delete(device)
    db.commit()
    return True


def register_device_for_user(
    db: Session,
    user: User,
    data: DeviceSelfRegisterRequest,
) -> tuple[Device, str]:
    """Registro manual desde la app.

    El usuario recibe ``device_id`` y ``api_key`` una sola vez para grabarlos
    en el firmware del ESP32.
    """
    _ensure_user_capacity(db, user.id)
    _ensure_global_capacity(db)

    device_id = (data.device_id or "").strip() or _generate_device_id(db)
    mac_address = _normalize_mac(data.mac_address)
    _ensure_device_id_available(db, device_id)
    _ensure_mac_available(db, mac_address)

    api_key = _generate_api_key()
    device = Device(
        device_id=device_id,
        name=data.name.strip() or "Mi sensor",
        location=(data.location or "").strip() or None,
        mac_address=mac_address,
        api_key=hash_device_key(api_key),
        is_active=True,
        user_id=user.id,
    )
    db.add(device)
    _commit_device(db, device)
    return device, api_key


def provision_device(
    db: Session,
    data: DeviceProvisionRequest,
) -> tuple[Device, str, str]:
    """Registra o reutiliza un ESP32 sin propietario y genera un código.

    El ESP32 llama a este endpoint al arrancar. Si ya está vinculado a una
    cuenta, se rechaza para no revelar la ``api_key`` de otro dispositivo.

    La clave se devuelve en claro una sola vez y se guarda como HMAC. En cada
    aprovisionamiento de un equipo aún no vinculado se rota la clave, de modo
    que una credencial vieja no pueda seguir enviando datos.
    """
    settings = get_settings()
    device_id = (data.device_id or "").strip() or None
    mac_address = _normalize_mac(data.mac_address)

    device: Device | None = None
    if device_id is not None:
        device = get_device_by_device_id(db, device_id)
    if device is None and mac_address is not None:
        device = db.scalar(select(Device).where(Device.mac_address == mac_address))

    api_key = _generate_api_key()
    if device is not None:
        if device.user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El dispositivo ya está vinculado a una cuenta",
            )
        if device_id is not None and device.device_id != device_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "La dirección MAC ya pertenece al dispositivo "
                    f"{device.device_id}"
                ),
            )
        _ensure_mac_available(db, mac_address, exclude_device_id=device.id)
        if data.name is not None and data.name.strip():
            device.name = data.name.strip()
        if data.location is not None:
            device.location = data.location.strip() or None
        if mac_address is not None:
            device.mac_address = mac_address
        device.is_active = True
        device.last_seen = _now()
        device.api_key = hash_device_key(api_key)
    else:
        _ensure_global_capacity(db)
        if device_id is None:
            device_id = _generate_device_id(db)
        else:
            _ensure_device_id_available(db, device_id)
        _ensure_mac_available(db, mac_address)
        device = Device(
            device_id=device_id,
            name=(data.name or "Sensor ESP32").strip() or "Sensor ESP32",
            location=(data.location or "").strip() or None,
            mac_address=mac_address,
            api_key=hash_device_key(api_key),
            is_active=True,
            user_id=None,
            last_seen=_now(),
        )
        db.add(device)

    code, code_hash = _generate_pairing_code(db)
    device.pairing_code_hash = code_hash
    device.pairing_expires_at = _now() + timedelta(
        minutes=settings.pairing_code_ttl_minutes
    )
    _commit_device(db, device)
    return device, code, api_key


def pair_device(db: Session, user: User, raw_code: str) -> Device:
    """Vincula un dispositivo pendiente a la cuenta que ingresa el código."""
    code = _normalize_pairing_code(raw_code)
    if len(code) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de emparejamiento debe tener 6 dígitos",
        )

    code_hash = _hash_pairing_code(code)
    device = db.scalar(
        select(Device).where(Device.pairing_code_hash == code_hash)
    )
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de emparejamiento inválido o vencido",
        )

    expires_at = as_local(device.pairing_expires_at)
    if expires_at is None or expires_at <= _now():
        device.pairing_code_hash = None
        device.pairing_expires_at = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de emparejamiento inválido o vencido",
        )

    if device.user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El dispositivo ya está vinculado a una cuenta",
        )
    if not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El dispositivo está desactivado",
        )

    _ensure_user_capacity(db, user.id)

    # Actualización atómica para que dos usuarios no puedan canjear el mismo
    # código al mismo tiempo.
    result = db.execute(
        update(Device)
        .where(
            Device.id == device.id,
            Device.user_id.is_(None),
            Device.pairing_code_hash == code_hash,
        )
        .values(
            user_id=user.id,
            is_active=True,
            pairing_code_hash=None,
            pairing_expires_at=None,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El dispositivo ya fue vinculado por otra cuenta",
        )

    # Las lecturas enviadas mientras el dispositivo no tenía dueño pasan a
    # formar parte del historial de la cuenta que lo vincula.
    db.execute(
        update(Measurement)
        .where(
            Measurement.device_id == device.id,
            Measurement.user_id.is_(None),
        )
        .values(user_id=user.id)
    )
    db.commit()
    db.refresh(device)
    return device


def rotate_api_key(db: Session, device_id: int, user: User) -> tuple[Device, str]:
    """Genera una api_key nueva; la anterior deja de funcionar de inmediato."""
    device = get_device(db, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )
    if user.role != UserRole.ADMIN.value and device.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes cambiar la clave de este dispositivo",
        )

    api_key = _generate_api_key()
    device.api_key = hash_device_key(api_key)
    db.add(device)
    _commit_device(db, device)
    return device, api_key


def unpair_device(db: Session, device_id: int, user: User) -> Device:
    """Desvincula un dispositivo sin borrar su historial de mediciones."""
    device = get_device(db, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado",
        )
    if user.role != UserRole.ADMIN.value and device.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes desvincular este dispositivo",
        )

    device.user_id = None
    device.is_active = False
    device.pairing_code_hash = None
    device.pairing_expires_at = None
    # La clave anterior deja de servir de inmediato. Si el mismo ESP32 vuelve
    # a aprovisionarse, recibirá una clave nueva y la guardará en su flash.
    device.api_key = hash_device_key(_generate_api_key())
    db.add(device)
    return _commit_device(db, device)


def device_capacity(db: Session, user: User) -> DeviceCapacity:
    settings = get_settings()
    registered = count_devices(db)
    user_devices = _count_user_devices(db, user.id)
    available = max(0, settings.max_devices - registered)
    return DeviceCapacity(
        max_devices=settings.max_devices,
        registered_devices=registered,
        available_slots=available,
        max_devices_per_user=settings.max_devices_per_user,
        user_devices=user_devices,
        can_register=(
            available > 0
            and user_devices < settings.max_devices_per_user
        ),
    )


def heartbeat(db: Session, device: Device) -> Device:
    """Marca el último contacto del dispositivo con el servidor."""
    device.last_seen = _now()
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def measurements_of_device(
    db: Session, device: Device, limit: int = 50
) -> list[Measurement]:
    """Historial del dispositivo limitado a su propietario actual.

    ``measurements.user_id`` se escribe al recibir la lectura y no cambia si el
    dispositivo se reasigna. El filtro evita que el nuevo dueño vea lecturas
    que pertenecen a otra cuenta.
    """
    statement = select(Measurement).where(Measurement.device_id == device.id)
    if device.user_id is None:
        statement = statement.where(Measurement.user_id.is_(None))
    else:
        statement = statement.where(Measurement.user_id == device.user_id)
    return db.scalars(
        statement.order_by(Measurement.measured_at.desc()).limit(limit)
    ).all()


def latest_measurement_of_device(
    db: Session, device: Device
) -> Measurement | None:
    """Última medición del propietario actual, o ``None`` si no hay."""
    statement = select(Measurement).where(Measurement.device_id == device.id)
    if device.user_id is None:
        statement = statement.where(Measurement.user_id.is_(None))
    else:
        statement = statement.where(Measurement.user_id == device.user_id)
    return db.scalar(statement.order_by(Measurement.measured_at.desc()).limit(1))

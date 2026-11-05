from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.time import as_local


class DeviceBase(BaseModel):
    device_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    location: Optional[str] = Field(default=None, max_length=100)
    mac_address: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = True
    user_id: Optional[int] = Field(default=None, gt=0)


class DeviceCreate(DeviceBase):
    api_key: str = Field(min_length=16, max_length=64)


class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    location: Optional[str] = Field(default=None, max_length=100)
    mac_address: Optional[str] = Field(default=None, max_length=20)
    api_key: Optional[str] = Field(default=None, min_length=16, max_length=64)
    is_active: Optional[bool] = None
    user_id: Optional[int] = Field(default=None, gt=0)


class DevicePublic(DeviceBase):
    """Datos del dispositivo seguros para el navegador.

    No incluye ``api_key``: esa clave solo la usa el ESP32 para autenticarse.
    """

    id: int
    owner_name: Optional[str] = None
    is_paired: bool = False
    last_seen: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_seen", "created_at")
    def serialize_dates(self, value: datetime | None) -> str | None:
        return as_local(value).isoformat() if value is not None else None


class DeviceProvisionRequest(BaseModel):
    """Datos que envía el ESP32 al solicitar un código de emparejamiento."""

    device_id: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    location: Optional[str] = Field(default=None, max_length=100)
    mac_address: Optional[str] = Field(default=None, max_length=20)


class DevicePairRequest(BaseModel):
    """Código de 6 dígitos que el usuario copia del monitor serial del ESP32."""

    pairing_code: str = Field(min_length=1, max_length=20)


class DeviceSelfRegisterRequest(BaseModel):
    """Registro manual desde la app: el usuario recibe la api_key una sola vez."""

    device_id: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: str = Field(default="Mi sensor", min_length=1, max_length=100)
    location: Optional[str] = Field(default=None, max_length=100)
    mac_address: Optional[str] = Field(default=None, max_length=20)


class DeviceCredentials(BaseModel):
    """Credenciales para grabar en el firmware del ESP32."""

    device: DevicePublic
    api_key: str
    message: str


class DeviceProvisioned(BaseModel):
    """Respuesta del aprovisionamiento: credenciales y código temporal."""

    device_id: str
    api_key: str
    pairing_code: str
    pairing_expires_at: datetime
    max_devices: int
    registered_devices: int
    message: str

    @field_serializer("pairing_expires_at")
    def serialize_pairing_expires_at(self, value: datetime) -> str:
        return as_local(value).isoformat()


class DeviceKeyRotated(BaseModel):
    """Nueva api_key generada para un dispositivo existente."""

    device_id: str
    api_key: str
    message: str


class DeviceCapacity(BaseModel):
    """Capacidad del servidor y del usuario actual."""

    max_devices: int
    registered_devices: int
    available_slots: int
    max_devices_per_user: int
    user_devices: int
    can_register: bool


class DeviceHeartbeat(BaseModel):
    device_id: str
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("last_seen")
    def serialize_last_seen(self, value: datetime) -> str:
        return as_local(value).isoformat()


class DeviceLatestMeasurement(BaseModel):
    """Última medición de un dispositivo ESP32 para el panel de signos vitales."""

    device_id: str
    spo2: int | None = None
    heart_rate_bpm: int | None = None
    source: str | None = None
    taken_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("taken_at")
    def serialize_taken_at(self, value: datetime | None) -> str | None:
        return as_local(value).isoformat() if value is not None else None


class DeviceMeasurementIngest(BaseModel):
    """Payload que envía cada ESP32 al backend.

    Solo se aceptan los campos fisiológicos y el origen. Cualquier intento de
    incluir ``user_id`` u otro campo se rechaza para que el propietario del
    registro siempre se derive de la credencial del dispositivo.
    """

    spo2: int = Field(ge=0, le=100)
    heart_rate_bpm: int | None = Field(default=None, ge=20, le=300)
    source: Literal["esp32", "simulator", "demo"] = "esp32"

    model_config = ConfigDict(extra="forbid")

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.time import as_local, as_utc
from app.schemas.device import DevicePublic


class CarePersonPublic(BaseModel):
    id: int
    full_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class CareAssignmentPublic(BaseModel):
    id: int
    patient_id: int
    member_id: int
    relationship: str
    is_active: bool
    created_at: datetime
    patient: CarePersonPublic
    member: CarePersonPublic

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        # SQLite devuelve la fecha sin zona, pero se guardó en UTC.
        return as_utc(value).astimezone().isoformat()


class CareAssignmentCreate(BaseModel):
    patient_id: int = Field(gt=0)
    member_id: int = Field(gt=0)
    relationship: Literal["coach"]


class PatientVitals(BaseModel):
    spo2: int | None = None
    heart_rate_bpm: int | None = None
    source: str | None = None
    taken_at: datetime | None = None
    status: Literal["normal", "review", "critical", "no_data"] = "no_data"
    alerts: list[str] = Field(default_factory=list)

    @field_serializer("taken_at")
    def serialize_taken_at(self, value: datetime | None) -> str | None:
        return as_local(value).isoformat() if value is not None else None


class CareMeasurementPublic(BaseModel):
    id: int
    device_id: int | None = None
    spo2: int
    heart_rate_bpm: int | None = None
    source: str
    measured_at: datetime

    @field_serializer("measured_at")
    def serialize_measured_at(self, value: datetime) -> str:
        return as_local(value).isoformat()


class CarePatientSummary(BaseModel):
    assignment_id: int
    relationship: str
    patient: CarePersonPublic
    device_count: int
    device_names: list[str]
    last_seen: datetime | None = None
    latest: PatientVitals | None = None
    alerts: list[str] = Field(default_factory=list)
    attention_device: str | None = None
    status: Literal["normal", "review", "critical", "offline", "no_data"] = "no_data"

    @field_serializer("last_seen")
    def serialize_last_seen(self, value: datetime | None) -> str | None:
        return as_local(value).isoformat() if value is not None else None


class CarePatientDetail(CarePatientSummary):
    devices: list[DevicePublic] = Field(default_factory=list)
    measurements: list[CareMeasurementPublic] = Field(default_factory=list)

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.time import as_local


class MeasurementCreate(BaseModel):
    spo2: int = Field(ge=0, le=100)
    heart_rate_bpm: int | None = Field(default=None, ge=20, le=300)
    source: Literal["simulator", "esp32", "demo"] = "simulator"
    device_id: int | None = Field(default=None, gt=0)


class MeasurementPublic(MeasurementCreate):
    id: int
    user_id: int | None = None
    device_id: int | None = None
    measured_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("measured_at")
    def serialize_measured_at(self, value: datetime) -> str:
        return as_local(value).isoformat()

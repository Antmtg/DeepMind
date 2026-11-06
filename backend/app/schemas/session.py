from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.time import as_local


SessionKind = Literal["static", "co2", "o2", "breathing", "mixed"]


class ApneaSessionCreate(BaseModel):
    kind: SessionKind = "static"
    duration_s: int = Field(default=0, ge=0, le=7200)
    max_hold_s: int | None = Field(default=None, ge=0, le=1200)
    rounds_completed: int = Field(default=0, ge=0, le=50)
    rounds_total: int | None = Field(default=None, ge=1, le=50)
    contractions: int = Field(default=0, ge=0, le=200)
    spo2_min: int | None = Field(default=None, ge=0, le=100)
    heart_rate_avg: int | None = Field(default=None, ge=20, le=300)
    notes: str | None = Field(default=None, max_length=500)
    source: Literal["manual", "simulator", "demo"] = "manual"
    patient_id: int | None = Field(default=None, gt=0)


class ApneaSessionPublic(BaseModel):
    id: int
    user_id: int
    athlete_name: str | None = None
    kind: str
    duration_s: int
    max_hold_s: int | None = None
    rounds_completed: int
    rounds_total: int | None = None
    contractions: int
    spo2_min: int | None = None
    heart_rate_avg: int | None = None
    notes: str | None = None
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return as_local(value).isoformat()


class SessionSummaryPublic(BaseModel):
    patient_id: int
    patient_name: str
    total_sessions: int = 0
    sessions_30d: int = 0
    best_hold_s: int | None = None
    total_hold_s: int = 0
    last_session_at: datetime | None = None
    last_kind: str | None = None
    avg_spo2_min: int | None = None

    @field_serializer("last_session_at")
    def serialize_last_session_at(self, value: datetime | None) -> str | None:
        return as_local(value).isoformat() if value is not None else None


class TrainingPlanCreate(BaseModel):
    patient_id: int = Field(gt=0)
    kind: SessionKind = "co2"
    target_value: int | None = Field(default=None, ge=0, le=1200)
    rounds: int = Field(default=8, ge=1, le=50)
    notes: str | None = Field(default=None, max_length=500)
    due_date: datetime | None = None


class TrainingPlanPublic(BaseModel):
    id: int
    patient_id: int
    patient_name: str | None = None
    coach_id: int | None = None
    coach_name: str | None = None
    kind: str
    target_value: int | None = None
    rounds: int
    notes: str | None = None
    due_date: datetime | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("due_date", "created_at")
    def serialize_dates(self, value: datetime | None) -> str | None:
        return as_local(value).isoformat() if value is not None else None

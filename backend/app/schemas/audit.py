from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.core.time import as_utc


class AuditPublic(BaseModel):
    id: int
    user_id: int | None
    email_attempted: str | None
    action: str
    status: str
    detail: str
    ip_address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return as_utc(value).isoformat()

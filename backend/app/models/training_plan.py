from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class TrainingPlan(Base):
    """Plan o tabla que un entrenador asigna a un deportista."""

    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    coach_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    kind: Mapped[str] = mapped_column(String(20), default="co2")
    target_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rounds: Mapped[int] = mapped_column(Integer, default=8)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now().astimezone(),
        index=True,
    )

    patient: Mapped["User"] = relationship(foreign_keys=[patient_id])
    coach: Mapped["User | None"] = relationship(foreign_keys=[coach_id])

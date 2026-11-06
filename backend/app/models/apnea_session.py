from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ApneaSession(Base):
    """Una sesión de apnea registrada desde el panel del deportista.

    Guarda tanto el cronómetro libre como las tablas CO₂/O₂ y la respiración
    guiada. El entrenador puede consultar las sesiones de sus deportistas.
    """

    __tablename__ = "apnea_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), default="static", index=True)
    duration_s: Mapped[int] = mapped_column(Integer, default=0)
    max_hold_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rounds_completed: Mapped[int] = mapped_column(Integer, default=0)
    rounds_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contractions: Mapped[int] = mapped_column(Integer, default=0)
    spo2_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heart_rate_avg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now().astimezone(),
        index=True,
    )

    user: Mapped["User"] = relationship()

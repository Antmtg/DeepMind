from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Device(Base):
    """Un dispositivo ESP32 biométrico (hasta 3 simultáneos en el diseño actual).

    Cada ESP32 se identifica con un ``device_id`` legible (por ejemplo
    ``ESP32-O2T-01``) y autentica sus envíos mediante ``api_key``.
    Un dispositivo puede estar vinculado a un usuario (paciente, cuidador,
    especialista, etc.) para que solo ese usuario lo vea en su dashboard.
    """

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pairing_code_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    pairing_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now().astimezone(),
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )

    user: Mapped["User | None"] = relationship(back_populates="devices")
    measurements: Mapped[list["Measurement"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )

    @property
    def owner_name(self) -> str | None:
        """Nombre del usuario propietario, útil para las respuestas públicas."""
        return self.user.full_name if self.user is not None else None

    @property
    def is_paired(self) -> bool:
        """Indica si el dispositivo ya está vinculado a una cuenta."""
        return self.user_id is not None

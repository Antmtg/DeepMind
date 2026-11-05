from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserRole(StrEnum):
    ATHLETE = "athlete"
    COACH = "coach"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    measurements: Mapped[list["Measurement"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    devices: Mapped[list["Device"]] = relationship(back_populates="user")

    care_assignments_as_patient: Mapped[list["CareAssignment"]] = relationship(
        foreign_keys="CareAssignment.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    care_assignments_as_member: Mapped[list["CareAssignment"]] = relationship(
        foreign_keys="CareAssignment.member_id",
        back_populates="member",
        cascade="all, delete-orphan",
    )

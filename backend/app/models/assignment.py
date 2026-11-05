from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.database.base import Base


class CareAssignment(Base):
    """Vínculo autorizado entre un paciente y un cuidador o especialista.

    Una misma pareja paciente-miembro solo puede tener un vínculo. Si se
    desactiva, se conserva para mantener trazabilidad y se puede reactivar.
    """

    __tablename__ = "care_assignments"
    __table_args__ = (
        UniqueConstraint("patient_id", "member_id", name="uq_care_assignment_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    relationship: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    patient: Mapped["User"] = orm_relationship(
        foreign_keys=[patient_id], back_populates="care_assignments_as_patient"
    )
    member: Mapped["User"] = orm_relationship(
        foreign_keys=[member_id], back_populates="care_assignments_as_member"
    )

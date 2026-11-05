from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.assignment import CareAssignment
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.user import User, UserRole
from app.schemas.care import (
    CareAssignmentCreate,
    CareAssignmentPublic,
    CareMeasurementPublic,
    CarePatientDetail,
    CarePatientSummary,
    CarePersonPublic,
    PatientVitals,
)
from app.schemas.device import DevicePublic
from app.services.vitals_service import (
    measurement_status,
    vitals_from_measurement,
)


RECENT_WINDOW = timedelta(minutes=15)
ATTENTION_WINDOW = timedelta(hours=24)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.astimezone()
    return value.astimezone()


def _status_order(value: str) -> int:
    return {"normal": 0, "review": 1, "critical": 2}.get(value, 0)


def _assignment_options():
    return (
        joinedload(CareAssignment.patient),
        joinedload(CareAssignment.member),
    )


def get_active_assignment(
    db: Session, *, member_id: int, patient_id: int
) -> CareAssignment | None:
    return db.scalar(
        select(CareAssignment)
        .options(*_assignment_options())
        .where(
            CareAssignment.member_id == member_id,
            CareAssignment.patient_id == patient_id,
            CareAssignment.is_active.is_(True),
        )
    )


def _patient_summary(db: Session, assignment: CareAssignment) -> CarePatientSummary:
    patient = assignment.patient
    devices = db.scalars(
        select(Device)
        .where(Device.user_id == patient.id)
        .order_by(Device.created_at)
    ).all()
    device_ids = [device.id for device in devices]

    latest = None
    if device_ids:
        latest = db.scalar(
            select(Measurement)
            .where(
                Measurement.device_id.in_(device_ids),
                Measurement.user_id == patient.id,
            )
            .order_by(Measurement.measured_at.desc())
            .limit(1)
        )

    last_seen_values = [_aware(device.last_seen) for device in devices if device.last_seen]
    last_seen = max(last_seen_values) if last_seen_values else None
    latest_vitals = PatientVitals(**vitals_from_measurement(latest)) if latest else None

    # Revisa la última lectura de cada sensor para no perder una alerta de un
    # dispositivo que no sea el que envió la medición más reciente.
    now = datetime.now().astimezone()
    worst_status = "normal"
    alerts: list[str] = []
    attention_device = None
    for device in devices:
        device_latest = db.scalar(
            select(Measurement)
            .where(
                Measurement.device_id == device.id,
                Measurement.user_id == patient.id,
            )
            .order_by(Measurement.measured_at.desc())
            .limit(1)
        )
        if device_latest is None:
            continue
        measured_at = _aware(device_latest.measured_at)
        if measured_at is None or now - measured_at > ATTENTION_WINDOW:
            continue
        device_status, device_alerts = measurement_status(device_latest)
        if _status_order(device_status) > _status_order(worst_status):
            worst_status = device_status
            attention_device = device.name
        alerts.extend(f"{device.name}: {alert}" for alert in device_alerts)

    summary_status = "no_data"
    if latest_vitals is not None:
        if worst_status in ("critical", "review"):
            summary_status = worst_status
        else:
            latest_at = _aware(latest_vitals.taken_at)
            if latest_at is not None and now - latest_at <= RECENT_WINDOW:
                summary_status = "normal"
            else:
                summary_status = "offline"

    return CarePatientSummary(
        assignment_id=assignment.id,
        relationship=assignment.relationship,
        patient=CarePersonPublic.model_validate(patient),
        device_count=len(devices),
        device_names=[device.name for device in devices],
        last_seen=last_seen,
        latest=latest_vitals,
        alerts=alerts,
        attention_device=attention_device,
        status=summary_status,
    )


def list_patients_for_member(db: Session, member: User) -> list[CarePatientSummary]:
    assignments = db.scalars(
        select(CareAssignment)
        .options(*_assignment_options())
        .where(
            CareAssignment.member_id == member.id,
            CareAssignment.is_active.is_(True),
        )
        .order_by(CareAssignment.created_at)
    ).all()
    return [_patient_summary(db, assignment) for assignment in assignments]


def patient_detail_for_member(
    db: Session, member: User, patient_id: int, limit: int = 20
) -> CarePatientDetail:
    assignment = get_active_assignment(
        db, member_id=member.id, patient_id=patient_id
    )
    if assignment is None:
        patient = db.get(User, patient_id)
        if patient is None or patient.role != UserRole.ATHLETE.value:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paciente no encontrado",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes una asignación activa con este paciente",
        )

    summary = _patient_summary(db, assignment)
    devices = db.scalars(
        select(Device)
        .options(joinedload(Device.user))
        .where(Device.user_id == patient_id)
        .order_by(Device.created_at)
    ).all()
    device_ids = [device.id for device in devices]
    measurements = []
    if device_ids:
        rows = db.scalars(
            select(Measurement)
            .where(
                Measurement.device_id.in_(device_ids),
                Measurement.user_id == patient_id,
            )
            .order_by(Measurement.measured_at.desc())
            .limit(limit)
        ).all()
        measurements = [
            CareMeasurementPublic(
                id=row.id,
                device_id=row.device_id,
                spo2=row.spo2,
                heart_rate_bpm=row.heart_rate_bpm,
                source=row.source,
                measured_at=row.measured_at,
            )
            for row in rows
        ]

    return CarePatientDetail(
        **summary.model_dump(),
        devices=[DevicePublic.model_validate(device) for device in devices],
        measurements=measurements,
    )


def list_assignments(db: Session, include_inactive: bool = False) -> list[CareAssignment]:
    statement = (
        select(CareAssignment)
        .options(*_assignment_options())
        .order_by(CareAssignment.is_active.desc(), CareAssignment.created_at.desc())
    )
    if not include_inactive:
        statement = statement.where(CareAssignment.is_active.is_(True))
    return db.scalars(statement).all()


def create_assignment(db: Session, data: CareAssignmentCreate) -> CareAssignmentPublic:
    patient = db.get(User, data.patient_id)
    member = db.get(User, data.member_id)

    if patient is None or patient.role != UserRole.ATHLETE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El paciente indicado no existe o no tiene rol de paciente",
        )
    if (
        member is None
        or member.role != UserRole.COACH.value
        or not member.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El miembro debe ser un cuidador o especialista activo",
        )
    if data.relationship != member.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de vínculo debe coincidir con el rol del miembro",
        )
    if patient.id == member.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un usuario no puede asignarse a sí mismo",
        )

    existing = db.scalar(
        select(CareAssignment).where(
            CareAssignment.patient_id == patient.id,
            CareAssignment.member_id == member.id,
        )
    )
    if existing is not None:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esa asignación ya está activa",
            )
        existing.is_active = True
        existing.relationship = data.relationship
        db.commit()
        db.refresh(existing)
        return CareAssignmentPublic.model_validate(existing)

    assignment = CareAssignment(
        patient_id=patient.id,
        member_id=member.id,
        relationship=data.relationship,
        is_active=True,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return CareAssignmentPublic.model_validate(assignment)


def deactivate_assignment(db: Session, assignment_id: int) -> None:
    assignment = db.get(CareAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada",
        )
    assignment.is_active = False
    db.commit()

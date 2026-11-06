from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.apnea_session import ApneaSession
from app.models.assignment import CareAssignment
from app.models.training_plan import TrainingPlan
from app.models.user import User, UserRole
from app.schemas.care import CarePersonPublic
from app.schemas.session import (
    ApneaSessionCreate,
    ApneaSessionPublic,
    SessionSummaryPublic,
    TrainingPlanCreate,
    TrainingPlanPublic,
)
from app.services.audit_service import register_event


def _assigned_patient_ids(db: Session, coach_id: int) -> list[int]:
    return list(
        db.scalars(
            select(CareAssignment.patient_id).where(
                CareAssignment.member_id == coach_id,
                CareAssignment.is_active.is_(True),
            )
        ).all()
    )


def _athlete_or_404(db: Session, patient_id: int) -> User:
    patient = db.get(User, patient_id)
    if patient is None or patient.role != UserRole.ATHLETE.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deportista no encontrado",
        )
    return patient


def _assert_can_access_patient(db: Session, user: User, patient_id: int) -> None:
    if user.role == UserRole.ADMIN.value:
        return
    if user.role == UserRole.ATHLETE.value and user.id == patient_id:
        return
    if user.role == UserRole.COACH.value:
        if patient_id in _assigned_patient_ids(db, user.id):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes una asignación activa con este deportista",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permiso para ver esta información",
    )


def _session_public(row: ApneaSession) -> ApneaSessionPublic:
    return ApneaSessionPublic(
        id=row.id,
        user_id=row.user_id,
        athlete_name=row.user.full_name if row.user is not None else None,
        kind=row.kind,
        duration_s=row.duration_s,
        max_hold_s=row.max_hold_s,
        rounds_completed=row.rounds_completed,
        rounds_total=row.rounds_total,
        contractions=row.contractions,
        spo2_min=row.spo2_min,
        heart_rate_avg=row.heart_rate_avg,
        notes=row.notes,
        source=row.source,
        created_at=row.created_at,
    )


def _plan_public(row: TrainingPlan) -> TrainingPlanPublic:
    return TrainingPlanPublic(
        id=row.id,
        patient_id=row.patient_id,
        patient_name=row.patient.full_name if row.patient is not None else None,
        coach_id=row.coach_id,
        coach_name=row.coach.full_name if row.coach is not None else None,
        kind=row.kind,
        target_value=row.target_value,
        rounds=row.rounds,
        notes=row.notes,
        due_date=row.due_date,
        is_active=row.is_active,
        created_at=row.created_at,
    )


def list_athletes(db: Session, user: User) -> list[CarePersonPublic]:
    """Deportistas visibles para el usuario: propios, asignados o todos."""
    if user.role == UserRole.ATHLETE.value:
        return [CarePersonPublic.model_validate(user)]

    statement = (
        select(User)
        .where(User.role == UserRole.ATHLETE.value, User.is_active.is_(True))
        .order_by(User.full_name)
    )
    if user.role == UserRole.COACH.value:
        ids = _assigned_patient_ids(db, user.id)
        if not ids:
            return []
        statement = statement.where(User.id.in_(ids))
    return [CarePersonPublic.model_validate(row) for row in db.scalars(statement).all()]


def list_sessions(
    db: Session,
    user: User,
    *,
    patient_id: int | None = None,
    limit: int = 60,
) -> list[ApneaSessionPublic]:
    statement = (
        select(ApneaSession)
        .options(joinedload(ApneaSession.user))
        .order_by(ApneaSession.created_at.desc())
        .limit(limit)
    )

    if user.role == UserRole.ATHLETE.value:
        statement = statement.where(ApneaSession.user_id == user.id)
    elif user.role == UserRole.COACH.value:
        ids = _assigned_patient_ids(db, user.id)
        if patient_id is not None:
            _assert_can_access_patient(db, user, patient_id)
            ids = [patient_id]
        if not ids:
            return []
        statement = statement.where(ApneaSession.user_id.in_(ids))
    elif patient_id is not None:
        _athlete_or_404(db, patient_id)
        statement = statement.where(ApneaSession.user_id == patient_id)

    return [_session_public(row) for row in db.scalars(statement).all()]


def create_session(
    db: Session, user: User, data: ApneaSessionCreate
) -> ApneaSessionPublic:
    patient_id = data.patient_id or user.id
    _athlete_or_404(db, patient_id)
    _assert_can_access_patient(db, user, patient_id)

    row = ApneaSession(
        user_id=patient_id,
        kind=data.kind,
        duration_s=data.duration_s,
        max_hold_s=data.max_hold_s,
        rounds_completed=data.rounds_completed,
        rounds_total=data.rounds_total,
        contractions=data.contractions,
        spo2_min=data.spo2_min,
        heart_rate_avg=data.heart_rate_avg,
        notes=data.notes,
        source=data.source,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    register_event(
        db,
        action="APNEA_SESSION_CREATED",
        status="SUCCESS",
        detail=(
            f"Sesión de apnea registrada para el deportista #{patient_id} "
            f"({data.kind}, {data.duration_s}s)."
        ),
        user_id=user.id,
    )
    return _session_public(row)


def delete_session(db: Session, user: User, session_id: int) -> None:
    row = db.get(ApneaSession, session_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión no encontrada",
        )
    if user.role == UserRole.ATHLETE.value and row.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes eliminar sesiones de otro deportista",
        )
    if user.role == UserRole.COACH.value:
        _assert_can_access_patient(db, user, row.user_id)

    patient_id = row.user_id
    db.delete(row)
    db.commit()
    register_event(
        db,
        action="APNEA_SESSION_DELETED",
        status="SUCCESS",
        detail=f"Sesión de apnea #{session_id} eliminada (deportista #{patient_id}).",
        user_id=user.id,
    )


def session_summaries(
    db: Session, user: User, *, patient_id: int | None = None
) -> list[SessionSummaryPublic]:
    patients = list_athletes(db, user)
    if patient_id is not None:
        _assert_can_access_patient(db, user, patient_id)
        patients = [p for p in patients if p.id == patient_id]
        if not patients:
            patients = [CarePersonPublic.model_validate(_athlete_or_404(db, patient_id))]

    now = datetime.now().astimezone()
    cutoff = now - timedelta(days=30)
    summaries: list[SessionSummaryPublic] = []

    for patient in patients:
        rows = db.scalars(
            select(ApneaSession)
            .where(ApneaSession.user_id == patient.id)
            .order_by(ApneaSession.created_at.desc())
        ).all()
        if not rows:
            summaries.append(
                SessionSummaryPublic(
                    patient_id=patient.id,
                    patient_name=patient.full_name,
                )
            )
            continue

        holds = [row.max_hold_s for row in rows if row.max_hold_s]
        spo2_values = [row.spo2_min for row in rows if row.spo2_min]
        recent = [row for row in rows if row.created_at and _is_after(row.created_at, cutoff)]
        summaries.append(
            SessionSummaryPublic(
                patient_id=patient.id,
                patient_name=patient.full_name,
                total_sessions=len(rows),
                sessions_30d=len(recent),
                best_hold_s=max(holds) if holds else None,
                total_hold_s=sum(row.duration_s or 0 for row in rows),
                last_session_at=rows[0].created_at,
                last_kind=rows[0].kind,
                avg_spo2_min=round(sum(spo2_values) / len(spo2_values))
                if spo2_values
                else None,
            )
        )
    return summaries


def _is_after(value: datetime, cutoff: datetime) -> bool:
    if value.tzinfo is None:
        value = value.astimezone()
    return value >= cutoff


def list_plans(
    db: Session,
    user: User,
    *,
    patient_id: int | None = None,
    include_inactive: bool = False,
    limit: int = 100,
) -> list[TrainingPlanPublic]:
    statement = (
        select(TrainingPlan)
        .options(
            joinedload(TrainingPlan.patient),
            joinedload(TrainingPlan.coach),
        )
        .order_by(TrainingPlan.is_active.desc(), TrainingPlan.created_at.desc())
        .limit(limit)
    )
    if not include_inactive:
        statement = statement.where(TrainingPlan.is_active.is_(True))

    if user.role == UserRole.ATHLETE.value:
        statement = statement.where(TrainingPlan.patient_id == user.id)
    elif user.role == UserRole.COACH.value:
        if patient_id is not None:
            _assert_can_access_patient(db, user, patient_id)
            statement = statement.where(TrainingPlan.patient_id == patient_id)
        else:
            ids = _assigned_patient_ids(db, user.id)
            if not ids:
                return []
            statement = statement.where(TrainingPlan.patient_id.in_(ids))
    elif patient_id is not None:
        _athlete_or_404(db, patient_id)
        statement = statement.where(TrainingPlan.patient_id == patient_id)

    return [_plan_public(row) for row in db.scalars(statement).all()]


def create_plan(db: Session, user: User, data: TrainingPlanCreate) -> TrainingPlanPublic:
    _athlete_or_404(db, data.patient_id)
    if user.role == UserRole.ATHLETE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un entrenador o administrador puede asignar planes",
        )
    _assert_can_access_patient(db, user, data.patient_id)

    row = TrainingPlan(
        patient_id=data.patient_id,
        coach_id=user.id if user.role == UserRole.COACH.value else None,
        kind=data.kind,
        target_value=data.target_value,
        rounds=data.rounds,
        notes=data.notes,
        due_date=data.due_date,
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    register_event(
        db,
        action="TRAINING_PLAN_CREATED",
        status="SUCCESS",
        detail=(
            f"Plan {data.kind} asignado al deportista #{data.patient_id} "
            f"({data.rounds} rondas)."
        ),
        user_id=user.id,
    )
    return _plan_public(row)


def deactivate_plan(db: Session, user: User, plan_id: int) -> None:
    row = db.get(TrainingPlan, plan_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan no encontrado",
        )
    if user.role == UserRole.ATHLETE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un entrenador o administrador puede archivar planes",
        )
    _assert_can_access_patient(db, user, row.patient_id)

    row.is_active = False
    db.commit()
    register_event(
        db,
        action="TRAINING_PLAN_ARCHIVED",
        status="SUCCESS",
        detail=f"Plan #{plan_id} archivado (deportista #{row.patient_id}).",
        user_id=user.id,
    )

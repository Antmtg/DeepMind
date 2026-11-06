from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.session import TrainingPlanCreate, TrainingPlanPublic
from app.services.session_service import (
    create_plan,
    deactivate_plan,
    list_plans,
)


router = APIRouter(prefix="/plans", tags=["Planes de entrenamiento"])


@router.get("", response_model=list[TrainingPlanPublic])
def plans(
    patient_id: int | None = Query(default=None, ge=1),
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(
        require_roles(UserRole.ATHLETE, UserRole.COACH, UserRole.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    return list_plans(
        db,
        current_user,
        patient_id=patient_id,
        include_inactive=include_inactive,
        limit=limit,
    )


@router.post(
    "",
    response_model=TrainingPlanPublic,
    status_code=status.HTTP_201_CREATED,
)
def new_plan(
    data: TrainingPlanCreate,
    current_user: User = Depends(require_roles(UserRole.COACH, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return create_plan(db, current_user, data)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_plan(
    plan_id: int = Path(ge=1),
    current_user: User = Depends(require_roles(UserRole.COACH, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    deactivate_plan(db, current_user, plan_id)
    return None

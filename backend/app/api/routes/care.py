from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.care import (
    CareAssignmentCreate,
    CareAssignmentPublic,
    CarePatientDetail,
    CarePatientSummary,
)
from app.services.care_service import (
    create_assignment,
    deactivate_assignment,
    list_assignments,
    list_patients_for_member,
    patient_detail_for_member,
)


router = APIRouter(prefix="/care", tags=["Cuidado"])


@router.get("/patients", response_model=list[CarePatientSummary])
def my_patients(
    current_user: User = Depends(
        require_roles(UserRole.COACH, UserRole.COACH)
    ),
    db: Session = Depends(get_db),
):
    """Pacientes con una asignación activa para el cuidador o especialista."""
    return list_patients_for_member(db, current_user)


@router.get("/patients/{patient_id}", response_model=CarePatientDetail)
def my_patient_detail(
    patient_id: int = Path(ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(
        require_roles(UserRole.COACH, UserRole.COACH)
    ),
    db: Session = Depends(get_db),
):
    return patient_detail_for_member(db, current_user, patient_id, limit=limit)


@router.get(
    "/assignments",
    response_model=list[CareAssignmentPublic],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def assignments(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return list_assignments(db, include_inactive=include_inactive)


@router.post(
    "/assignments",
    response_model=CareAssignmentPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def new_assignment(
    data: CareAssignmentCreate,
    db: Session = Depends(get_db),
):
    return create_assignment(db, data)


@router.delete(
    "/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def remove_assignment(
    assignment_id: int = Path(ge=1),
    db: Session = Depends(get_db),
):
    deactivate_assignment(db, assignment_id)
    return None

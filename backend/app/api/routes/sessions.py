from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.care import CarePersonPublic
from app.schemas.session import (
    ApneaSessionCreate,
    ApneaSessionPublic,
    SessionSummaryPublic,
)
from app.services.session_service import (
    create_session,
    delete_session,
    list_athletes,
    list_sessions,
    session_summaries,
)


router = APIRouter(prefix="/sessions", tags=["Sesiones de apnea"])


@router.get("", response_model=list[ApneaSessionPublic])
def sessions(
    patient_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=60, ge=1, le=200),
    current_user: User = Depends(
        require_roles(UserRole.ATHLETE, UserRole.COACH, UserRole.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    return list_sessions(db, current_user, patient_id=patient_id, limit=limit)


@router.get("/summary", response_model=list[SessionSummaryPublic])
def summaries(
    patient_id: int | None = Query(default=None, ge=1),
    current_user: User = Depends(
        require_roles(UserRole.ATHLETE, UserRole.COACH, UserRole.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    return session_summaries(db, current_user, patient_id=patient_id)


@router.get("/athletes", response_model=list[CarePersonPublic])
def athletes(
    current_user: User = Depends(
        require_roles(UserRole.ATHLETE, UserRole.COACH, UserRole.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    return list_athletes(db, current_user)


@router.post(
    "",
    response_model=ApneaSessionPublic,
    status_code=status.HTTP_201_CREATED,
)
def new_session(
    data: ApneaSessionCreate,
    current_user: User = Depends(
        require_roles(UserRole.ATHLETE, UserRole.COACH, UserRole.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    return create_session(db, current_user, data)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_session(
    session_id: int = Path(ge=1),
    current_user: User = Depends(
        require_roles(UserRole.ATHLETE, UserRole.COACH, UserRole.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    delete_session(db, current_user, session_id)
    return None

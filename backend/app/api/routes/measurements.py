from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.measurement import (
    MeasurementCreate,
    MeasurementPublic,
)
from app.services.measurement_service import create_measurement


router = APIRouter(prefix="/measurements", tags=["Mediciones"])


@router.post(
    "",
    response_model=MeasurementPublic,
    status_code=status.HTTP_201_CREATED,
)
def register_measurement(
    data: MeasurementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_measurement(db, data, current_user)

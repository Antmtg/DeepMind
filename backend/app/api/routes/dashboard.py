from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.dashboard import DashboardResponse
from app.schemas.user import UserPublic
from app.services.role_service import ROLE_DASHBOARDS


router = APIRouter(prefix="/dashboard", tags=["Panel"])


@router.get("", response_model=DashboardResponse)
def dashboard(current_user: User = Depends(get_current_user)):
    content = ROLE_DASHBOARDS[UserRole(current_user.role)]
    return DashboardResponse(user=UserPublic.model_validate(current_user), **content)

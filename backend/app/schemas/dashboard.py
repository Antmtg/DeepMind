from pydantic import BaseModel

from app.schemas.user import UserPublic


class DashboardResponse(BaseModel):
    user: UserPublic
    title: str
    description: str
    permissions: list[str]
    next_module: str

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database.session import get_db
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.schemas.audit import AuditPublic


router = APIRouter(prefix="/audit", tags=["Auditoría"])


@router.get("", response_model=list[AuditPublic])
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    action: str | None = Query(default=None),
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    statement = select(AuditLog).order_by(AuditLog.created_at.desc())
    if status_filter:
        statement = statement.where(AuditLog.status == status_filter.upper())
    if action:
        statement = statement.where(AuditLog.action == action.upper())
    statement = statement.offset(offset).limit(limit)
    return db.scalars(statement).all()

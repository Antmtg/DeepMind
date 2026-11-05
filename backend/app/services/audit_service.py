from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def register_event(
    db: Session,
    *,
    action: str,
    status: str,
    detail: str,
    user_id: int | None = None,
    email_attempted: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    event = AuditLog(
        user_id=user_id,
        email_attempted=email_attempted,
        action=action,
        status=status,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

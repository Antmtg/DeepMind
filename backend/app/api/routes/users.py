from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserAdmin, UserAdminUpdate, UserCreate
from app.services.audit_service import register_event
from app.services.user_service import create_user, update_user


router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("", response_model=list[UserAdmin])
def list_users(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("", response_model=UserAdmin, status_code=status.HTTP_201_CREATED)
def create_user_account(
    data: UserCreate,
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    user = create_user(db, data)
    register_event(
        db,
        action="USER_CREATED",
        status="SUCCESS",
        detail=f"Alta de cuenta nueva con rol {user.role}",
        user_id=admin.id,
        email_attempted=user.email,
        ip_address=request.client.host if request.client else None,
    )
    return user


@router.patch("/{user_id}", response_model=UserAdmin)
def patch_user_account(
    user_id: int,
    data: UserAdminUpdate,
    request: Request,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Esa cuenta no existe.",
        )

    cambio = [campo for campo in ("full_name", "role", "is_active") if getattr(data, campo) is not None]
    cambio_pasword = data.password is not None

    user = update_user(db, user_id, data)
    if cambio_pasword:
        register_event(
            db,
            action="USER_PASSWORD_RESET",
            status="SUCCESS",
            detail="El administrador asignó una contraseña nueva",
            user_id=admin.id,
            email_attempted=user.email,
            ip_address=request.client.host if request.client else None,
        )
    if cambio:
        register_event(
            db,
            action="USER_UPDATED",
            status="SUCCESS",
            detail="Cambios: " + ", ".join(cambio),
            user_id=admin.id,
            email_attempted=user.email,
            ip_address=request.client.host if request.client else None,
        )
    elif not cambio_pasword:
        register_event(
            db,
            action="USER_UPDATED",
            status="SUCCESS",
            detail="Sin cambios efectivos",
            user_id=admin.id,
            email_attempted=user.email,
            ip_address=request.client.host if request.client else None,
        )
    return user

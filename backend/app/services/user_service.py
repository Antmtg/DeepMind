"""Alta y gestión administrativa de cuentas.

Las cuentas se crean desde el panel de administración: nosotros entregamos el
correo del estudiante y asignamos la contraseña en persona. No existe
autoregistro por diseño.
"""

import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserAdminUpdate, UserCreate

PASSWORD_MIN_LENGTH = 8
_PASSWORD_LETTER = re.compile(r"[A-Za-zñÑ]")
_PASSWORD_DIGIT = re.compile(r"\d")


def _normalizar_rol(role: str) -> str:
    try:
        return UserRole(role).value
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rol no válido. Usa: athlete, coach o admin.",
        ) from exc


def validar_password(password: str, email: str) -> str:
    """Contraseña con al menos 8 caracteres, una letra y un número.

    Nunca se guarda el texto: solo se usa para generar el hash Argon2id.
    """
    email = email.lower()
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"La contraseña necesita al menos {PASSWORD_MIN_LENGTH} caracteres.",
        )
    if not _PASSWORD_LETTER.search(password) or not _PASSWORD_DIGIT.search(password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La contraseña necesita al menos una letra y un número.",
        )
    usuario = email.split("@")[0] if "@" in email else email
    if len(usuario) >= 4 and usuario in password.lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La contraseña no debe contener tu nombre de usuario.",
        )
    return password


def _asegurar_correo_disponible(db: Session, email: str) -> str:
    email = email.lower()
    existente = db.scalar(select(User).where(User.email == email))
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese correo ya está registrado.",
        )
    return email


def _contar_admins_activos(db: Session) -> int:
    return len(
        db.scalars(
            select(User).where(
                User.role == UserRole.ADMIN.value,
                User.is_active.is_(True),
            )
        ).all()
    )


def create_user(db: Session, data: UserCreate) -> User:
    email = _asegurar_correo_disponible(db, data.email)
    validar_password(data.password, email)
    user = User(
        full_name=data.full_name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        role=_normalizar_rol(data.role),
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def update_user(db: Session, user_id: int, data: UserAdminUpdate) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Esa cuenta no existe.",
        )

    cambio_rol = data.role is not None and data.role != user.role
    desactivar = data.is_active is False and user.is_active

    # Protege la última cuenta admin activa del sistema.
    if user.role == UserRole.ADMIN.value and (cambio_rol or desactivar):
        if _contar_admins_activos(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Debe existir al menos un administrador activo.",
            )

    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    if data.role is not None:
        user.role = _normalizar_rol(data.role)
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password:
        validar_password(data.password, user.email)
        user.password_hash = hash_password(data.password)
    db.commit()
    return user

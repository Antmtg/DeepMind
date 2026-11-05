from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer

from app.core.time import as_utc


class UserPublic(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserAdmin(UserPublic):
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return as_utc(value).isoformat()


class UserCreate(BaseModel):
    """Alta de cuenta nueva hecha por el administrador.

    Nosotros entregamos el correo y asignamos la contraseña; el usuario
    nunca se registra solo.
    """

    full_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    role: str
    password: str = Field(min_length=8, max_length=128)


class UserAdminUpdate(BaseModel):
    """Cambios administrativos: datos, rol, estado y contraseña."""

    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    role: str | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

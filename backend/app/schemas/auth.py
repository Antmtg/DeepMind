from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserPublic


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    """La usuaria entra con la contraseña primaria que le asignamos y la cambia."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class LoginResponse(BaseModel):
    message: str
    user: UserPublic
    expires_in_minutes: int


class MessageResponse(BaseModel):
    message: str

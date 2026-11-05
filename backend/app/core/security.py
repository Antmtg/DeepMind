from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import get_settings


# PasswordHash.recommended() usa Argon2id y genera un salt diferente en cada hash.
password_hash = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    """Convierte una contraseña en un hash; nunca guardamos el texto original."""
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Compara sin descifrar: la contraseña original no se puede recuperar."""
    return password_hash.verify(plain_password, stored_hash)


def create_access_token(user_id: int, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except InvalidTokenError as error:
        raise ValueError("Token inválido o vencido") from error

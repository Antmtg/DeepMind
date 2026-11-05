"""Protección de las credenciales de los ESP32.

La clave que se entrega al dispositivo se muestra una sola vez. En la base de
datos solo queda un HMAC-SHA256 calculado con ``SECRET_KEY``. Así, una copia de
la base de datos no permite suplantar a un ESP32.
"""

import hashlib
import hmac
import re

from app.core.config import get_settings


_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def hash_device_key(api_key: str) -> str:
    """Devuelve el valor que se guarda en la columna ``devices.api_key``."""
    settings = get_settings()
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        api_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def is_hashed_device_key(value: str | None) -> bool:
    """Reconoce un HMAC ya almacenado (64 caracteres hexadecimales)."""
    return bool(value and _HASH_PATTERN.fullmatch(value))

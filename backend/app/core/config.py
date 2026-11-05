from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Configuración que puede cambiar sin modificar el código."""

    app_name: str = "Deep Mind"
    app_env: str = "development"
    secret_key: str = "solo-desarrollo-cambiar-antes-de-publicar"
    access_token_expire_minutes: int = 30
    database_url: str = f"sqlite:///{BACKEND_DIR / 'deepmind.db'}"
    cookie_secure: bool = False

    # Datos de demostración. En un servidor casero real conviene desactivarlos
    # para no crear cuentas con contraseñas conocidas.
    seed_demo_data: bool = True

    # Capacidad del servidor casero: 3-5 ESP32 como máximo.
    max_devices: int = Field(default=5, ge=1, le=50)
    max_devices_per_user: int = Field(default=1, ge=1, le=50)

    # Emparejamiento de hardware.
    device_provisioning_key: str = "cambiar-clave-de-provisionamiento"
    pairing_code_ttl_minutes: int = Field(default=10, ge=1, le=60)
    pairing_max_attempts: int = Field(default=10, ge=1, le=100)
    pairing_attempt_window_seconds: int = Field(default=60, ge=1, le=3600)

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

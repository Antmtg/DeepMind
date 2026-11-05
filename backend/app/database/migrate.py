from sqlalchemy import text

from app.core.device_keys import hash_device_key, is_hashed_device_key
from app.database.base import Base
from app.database.session import engine
from app import models  # noqa: F401  # Registra modelos (Device, Measurement, User, Audit)


def _column_names(db_table: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({db_table})")).fetchall()
    return {row[1] for row in rows}


def migrate() -> None:
    """Ejecuta migraciones ligeras e idempotentes sobre SQLite.

    - Crea tablas nuevas (Device, etc.) si faltan.
    - Agrega columnas a tablas existentes sin borrar datos.
    """
    # 1. Tablas nuevas declaradas en los modelos.
    Base.metadata.create_all(bind=engine)

    # 2. Columnas nuevas en la tabla measurements (si faltan).
    measurement_cols = _column_names("measurements")
    with engine.begin() as conn:
        if "heart_rate_bpm" not in measurement_cols:
            conn.execute(
                text("ALTER TABLE measurements ADD COLUMN heart_rate_bpm INTEGER")
            )
        if "device_id" not in measurement_cols:
            conn.execute(
                text("ALTER TABLE measurements ADD COLUMN device_id INTEGER")
            )

    # 3. Columnas de emparejamiento en la tabla devices (si faltan).
    device_cols = _column_names("devices")
    with engine.begin() as conn:
        if "user_id" not in device_cols:
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN user_id INTEGER")
            )
        if "pairing_code_hash" not in device_cols:
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN pairing_code_hash VARCHAR(64)")
            )
        if "pairing_expires_at" not in device_cols:
            conn.execute(
                text("ALTER TABLE devices ADD COLUMN pairing_expires_at DATETIME")
            )
        # SQLite no permite agregar una restricción UNIQUE con ALTER TABLE,
        # así que creamos el índice único por separado.
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "ix_devices_pairing_code_hash ON devices (pairing_code_hash)"
            )
        )

    # 4. Las versiones anteriores guardaban la api_key del ESP32 en claro.
    #    Se reemplaza una sola vez por su HMAC; el firmware conserva su clave
    #    original y sigue autenticando porque el servidor calcula el mismo HMAC.
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, api_key FROM devices")).fetchall()
        for device_pk, stored_key in rows:
            if not stored_key or is_hashed_device_key(stored_key):
                continue
            conn.execute(
                text("UPDATE devices SET api_key = :key WHERE id = :id"),
                {"key": hash_device_key(stored_key), "id": device_pk},
            )

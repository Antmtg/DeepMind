from datetime import datetime, timezone


def as_local(value: datetime | None) -> datetime | None:
    """Convierte a la zona horaria local del servidor.

    SQLite guarda las fechas sin zona. Las mediciones y los contactos de los
    dispositivos se crean con la hora local, así que un valor sin zona se
    interpreta como local. Las fechas de auditoría y de creación de usuarios se
    guardan en UTC y se convierten con :func:`as_utc`.
    """

    if value is None:
        return None
    if value.tzinfo is None:
        return value.astimezone()
    return value.astimezone()


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

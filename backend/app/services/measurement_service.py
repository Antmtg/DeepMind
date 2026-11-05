from datetime import datetime

from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.measurement import Measurement
from app.models.user import User
from app.schemas.measurement import MeasurementCreate


def create_measurement(
    db: Session,
    data: MeasurementCreate,
    current_user: User | None = None,
    device: Device | None = None,
) -> Measurement:
    owner_id = current_user.id if current_user is not None else None
    if owner_id is None and device is not None:
        owner_id = device.user_id
    measured_at = datetime.now().astimezone()
    measurement = Measurement(
        user_id=owner_id,
        device_id=device.id if device is not None else None,
        spo2=data.spo2,
        heart_rate_bpm=data.heart_rate_bpm,
        source=data.source,
        measured_at=measured_at,
    )
    db.add(measurement)
    if device is not None:
        # Cada lectura también confirma que el ESP32 sigue en línea. Así el
        # panel no depende exclusivamente del heartbeat.
        device.last_seen = measured_at
        db.add(device)
    db.commit()
    db.refresh(measurement)
    return measurement

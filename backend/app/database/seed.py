import secrets
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.device_keys import hash_device_key
from app.core.security import hash_password
from app.models.assignment import CareAssignment
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.user import User, UserRole


DEMO_USERS = [
    ("Deportista Demo", "deportista.deepmind.demo@gmail.com", UserRole.ATHLETE),
    ("Entrenador Demo", "entrenador.deepmind.demo@gmail.com", UserRole.COACH),
    ("Administrador Demo", "admin.deepmind.demo@gmail.com", UserRole.ADMIN),
    # Deportistas adicionales para demostrar separación de datos.
    ("Deportista Demo Dos", "deportista2.deepmind.demo@gmail.com", UserRole.ATHLETE),
    ("Deportista Demo Tres", "deportista3.deepmind.demo@gmail.com", UserRole.ATHLETE),
]

DEMO_DEVICES = [
    (
        "ESP32-DM-01",
        "Sensor A · piscina",
        "Piscina principal",
        "AA:BB:CC:DD:EE:01",
    ),
    (
        "ESP32-DM-02",
        "Sensor B · seco",
        "Zona de apnea en seco",
        "AA:BB:CC:DD:EE:02",
    ),
    (
        "ESP32-DM-03",
        "Sensor C · reserva",
        "Sin ubicación",
        "AA:BB:CC:DD:EE:03",
    ),
]

# Lecturas de ejemplo. La primera lectura de cada sensor es la más reciente.
# Se marcan como ``demo`` para no confundirlas con datos reales del ESP32.
DEMO_MEASUREMENTS = {
    "ESP32-DM-01": [
        (2, 97, 72, "demo"),
        (9, 96, 75, "demo"),
        (24, 98, 70, "demo"),
        (44, 97, 74, "demo"),
        (69, 96, 78, "demo"),
    ],
    "ESP32-DM-02": [
        (1, 93, 88, "demo"),
        (19, 95, 82, "demo"),
    ],
    "ESP32-DM-03": [],
}


def seed_demo_users(db: Session) -> None:
    """Crea las cuentas demo que falten, sin modificar las existentes."""
    created = False
    for full_name, email, role in DEMO_USERS:
        existing = db.scalar(select(User.id).where(User.email == email))
        if existing is not None:
            continue
        db.add(
            User(
                full_name=full_name,
                email=email,
                password_hash=hash_password("Practica4!"),
                role=role.value,
            )
        )
        created = True
    if created:
        db.commit()


def seed_demo_devices(db: Session) -> None:
    """Registra los 3 ESP32 y asigna uno a cada deportista demo."""
    athletes = db.scalars(
        select(User)
        .where(User.role == UserRole.ATHLETE.value)
        .order_by(User.id)
    ).all()
    if not athletes:
        return

    for index, (device_id, name, location, mac_address) in enumerate(DEMO_DEVICES):
        athlete = athletes[min(index, len(athletes) - 1)]
        device = db.scalar(select(Device).where(Device.device_id == device_id))
        if device is None:
            demo_key = secrets.token_urlsafe(32)
            db.add(
                Device(
                    device_id=device_id,
                    name=name,
                    location=location,
                    mac_address=mac_address,
                    api_key=hash_device_key(demo_key),
                    is_active=True,
                    user_id=athlete.id,
                )
            )
        else:
            device.name = name
            device.location = location
            device.mac_address = mac_address
            device.is_active = True
            device.user_id = athlete.id
    db.commit()


def seed_demo_assignments(db: Session) -> None:
    """Vincula al entrenador demo con el primer deportista demo."""
    athlete = db.scalar(
        select(User).where(User.role == UserRole.ATHLETE.value).order_by(User.id)
    )
    if athlete is None:
        return

    members = db.scalars(
        select(User).where(User.role == UserRole.COACH.value)
    ).all()
    for member in members:
        assignment = db.scalar(
            select(CareAssignment).where(
                CareAssignment.patient_id == athlete.id,
                CareAssignment.member_id == member.id,
            )
        )
        if assignment is None:
            db.add(
                CareAssignment(
                    patient_id=athlete.id,
                    member_id=member.id,
                    relationship=member.role,
                    is_active=True,
                )
            )
        else:
            assignment.relationship = member.role
            assignment.is_active = True
    db.commit()


def seed_demo_measurements(db: Session) -> None:
    """Crea lecturas de ejemplo una sola vez y actualiza el último contacto."""
    devices = db.scalars(
        select(Device).where(
            Device.device_id.in_(list(DEMO_MEASUREMENTS.keys()))
        )
    ).all()
    if not devices:
        return

    existing = db.scalar(
        select(Measurement.id)
        .where(Measurement.device_id.in_([device.id for device in devices]))
        .limit(1)
    )
    now = datetime.now().astimezone()

    if existing is None:
        for device in devices:
            for minutes_ago, spo2, heart_rate, source in DEMO_MEASUREMENTS[
                device.device_id
            ]:
                db.add(
                    Measurement(
                        user_id=device.user_id,
                        device_id=device.id,
                        spo2=spo2,
                        heart_rate_bpm=heart_rate,
                        source=source,
                        measured_at=now - timedelta(minutes=minutes_ago),
                    )
                )
        db.commit()

    for device in devices:
        latest = db.scalar(
            select(Measurement)
            .where(Measurement.device_id == device.id)
            .order_by(Measurement.measured_at.desc())
            .limit(1)
        )
        if latest is not None:
            device.last_seen = latest.measured_at

        db.execute(
            update(Measurement)
            .where(Measurement.device_id == device.id)
            .values(user_id=device.user_id)
        )
    db.commit()
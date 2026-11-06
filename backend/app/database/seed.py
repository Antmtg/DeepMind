import math
import secrets
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.device_keys import hash_device_key
from app.core.security import hash_password
from app.models.apnea_session import ApneaSession
from app.models.assignment import CareAssignment
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.training_plan import TrainingPlan
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
    """Vincula a los entrenadores demo con todos los deportistas demo."""
    athletes = db.scalars(
        select(User).where(User.role == UserRole.ATHLETE.value).order_by(User.id)
    ).all()
    if not athletes:
        return

    members = db.scalars(
        select(User).where(User.role == UserRole.COACH.value)
    ).all()
    for athlete in athletes:
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
    """Crea 60 días de lecturas de ejemplo por sensor (una sola vez)."""
    devices = db.scalars(
        select(Device)
        .where(Device.device_id.in_(list(DEMO_MEASUREMENTS.keys())))
        .order_by(Device.id)
    ).all()
    if not devices:
        return

    device_ids = [device.id for device in devices]
    existing = db.scalar(
        select(func.count(Measurement.id)).where(
            Measurement.device_id.in_(device_ids)
        )
    )
    now = datetime.now().astimezone()

    if existing < 40:
        for device_index, device in enumerate(devices):
            # Lecturas de hoy: la más reciente queda a 2 minutos del presente.
            for minutes_ago in (2, 9, 24, 44, 69):
                phase = minutes_ago * 0.12 + device_index * 1.3
                db.add(
                    Measurement(
                        user_id=device.user_id,
                        device_id=device.id,
                        spo2=max(92, min(99, 96 + round(2 * math.sin(phase)))),
                        heart_rate_bpm=68
                        + round(8 * math.sin(phase * 0.7))
                        + (4 if minutes_ago < 30 else 0),
                        source="demo",
                        measured_at=now - timedelta(minutes=minutes_ago),
                    )
                )

            # Historial de 60 días para que calendario, racha y tendencias
            # tengan datos reales que mostrar.
            for days_ago in range(1, 61):
                if (days_ago + device_index) % 11 == 0:
                    continue
                for slot, hour in enumerate((7, 11, 16, 20)):
                    phase = days_ago * 0.55 + slot * 0.8 + device_index * 1.3
                    spo2 = max(92, min(99, 96 + round(2.4 * math.sin(phase))))
                    if days_ago % 17 == 0 and slot == 3:
                        spo2 = max(90, spo2 - 3)
                    measured_at = (now - timedelta(days=days_ago)).replace(
                        hour=hour,
                        minute=(slot * 13 + device_index * 5) % 60,
                        second=0,
                        microsecond=0,
                    )
                    db.add(
                        Measurement(
                            user_id=device.user_id,
                            device_id=device.id,
                            spo2=spo2,
                            heart_rate_bpm=66
                            + round(9 * math.sin(phase * 0.7))
                            + (4 if 12 <= hour <= 18 else 0),
                            source="demo",
                            measured_at=measured_at,
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


SESSION_NOTES = [
    "Buen control de la relajación en las primeras rondas.",
    "Costó mantener la calma en la última serie.",
    "Sin contracciones incómodas. Buen ritmo.",
    "Ajustar el descanso: llegué justo a la siguiente ronda.",
    "Mejor sensación que la sesión anterior.",
    None,
]


def _ensure_demo_today_session(
    db: Session, athletes: list[User], now: datetime
) -> None:
    """Asegura que las cuentas demo tengan una sesión hoy (racha visible)."""
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    demo_athletes = [a for a in athletes if "deepmind.demo" in (a.email or "")]
    for index, athlete in enumerate(demo_athletes):
        exists = db.scalar(
            select(ApneaSession.id)
            .where(
                ApneaSession.user_id == athlete.id,
                ApneaSession.created_at >= today_start,
            )
            .limit(1)
        )
        if exists is not None:
            continue
        hold = 70 + index * 8
        db.add(
            ApneaSession(
                user_id=athlete.id,
                kind="static",
                duration_s=hold + 180,
                max_hold_s=hold,
                rounds_completed=3,
                rounds_total=4,
                contractions=1,
                spo2_min=95,
                heart_rate_avg=68 + index * 3,
                notes="Sesión corta de hoy: control de la respiración y una retención cómoda.",
                source="demo",
                created_at=now - timedelta(minutes=45 + index * 20),
            )
        )
    db.commit()


def seed_demo_sessions(db: Session) -> None:
    """Crea un historial de 45 días de sesiones de apnea por deportista."""
    athletes = db.scalars(
        select(User).where(User.role == UserRole.ATHLETE.value).order_by(User.id)
    ).all()
    if not athletes:
        return

    now = datetime.now().astimezone()
    existing = db.scalar(select(ApneaSession.id).limit(1))
    if existing is not None:
        _ensure_demo_today_session(db, athletes, now)
        return

    kinds = ("static", "co2", "o2", "breathing")

    for athlete_index, athlete in enumerate(athletes):
        for days_ago in range(46):
            if days_ago > 0 and (days_ago + athlete_index) % 3 == 0:
                continue
            seed = days_ago + athlete_index * 7
            kind = kinds[(days_ago + athlete_index) % len(kinds)]
            base_hold = 52 + athlete_index * 13 + round(11 * math.sin(seed * 0.33))

            if kind == "static":
                max_hold = base_hold + 18
                rounds_total = 6
            elif kind == "o2":
                max_hold = max(20, base_hold - 8)
                rounds_total = 8
            elif kind == "breathing":
                max_hold = None
                rounds_total = 10
            else:
                max_hold = base_hold
                rounds_total = 8

            rounds_completed = max(1, rounds_total - (seed % 3))
            duration_s = rounds_completed * (int(max_hold or 30) + 75)
            if kind == "breathing":
                duration_s += 60

            created_at = now - timedelta(
                days=days_ago,
                minutes=90 + ((athlete_index * 37 + days_ago * 53) % 600),
            )

            db.add(
                ApneaSession(
                    user_id=athlete.id,
                    kind=kind,
                    duration_s=duration_s,
                    max_hold_s=max_hold,
                    rounds_completed=rounds_completed,
                    rounds_total=rounds_total,
                    contractions=(
                        1 + (seed % 4) if kind in ("co2", "static") else 0
                    ),
                    spo2_min=max(
                        86,
                        min(
                            98,
                            94 - (seed % 5) + (2 if kind == "o2" else 0),
                        ),
                    ),
                    heart_rate_avg=62 + (seed % 18),
                    notes=SESSION_NOTES[seed % len(SESSION_NOTES)],
                    source="demo",
                    created_at=created_at,
                )
            )
    db.commit()


def seed_demo_plans(db: Session) -> None:
    """Asigna planes activos y uno archivado para la demo del entrenador."""
    existing = db.scalar(select(TrainingPlan.id).limit(1))
    if existing is not None:
        return

    coach = db.scalar(
        select(User).where(User.role == UserRole.COACH.value).order_by(User.id)
    )
    athletes = db.scalars(
        select(User).where(User.role == UserRole.ATHLETE.value).order_by(User.id)
    ).all()
    if not athletes:
        return

    now = datetime.now().astimezone()
    for index, athlete in enumerate(athletes):
        db.add(
            TrainingPlan(
                patient_id=athlete.id,
                coach_id=coach.id if coach else None,
                kind="co2",
                target_value=8,
                rounds=8,
                notes="Tabla CO₂: 8 rondas con 2:30 de recuperación. Para esta semana.",
                due_date=now + timedelta(days=5),
                is_active=True,
            )
        )
        db.add(
            TrainingPlan(
                patient_id=athlete.id,
                coach_id=coach.id if coach else None,
                kind="static",
                target_value=95 + index * 10,
                rounds=5,
                notes="Aguante estático controlado, siempre con compañero de seguridad.",
                due_date=now + timedelta(days=12),
                is_active=True,
            )
        )
        db.add(
            TrainingPlan(
                patient_id=athlete.id,
                coach_id=coach.id if coach else None,
                kind="breathing",
                target_value=None,
                rounds=10,
                notes="Respiración 4-4-6-2 para bajar pulsaciones antes de la apnea.",
                due_date=now + timedelta(days=2),
                is_active=True,
            )
        )

    if athletes:
        db.add(
            TrainingPlan(
                patient_id=athletes[0].id,
                coach_id=coach.id if coach else None,
                kind="o2",
                target_value=60,
                rounds=6,
                notes="Plan de la semana pasada. Archivado al completarse.",
                due_date=now - timedelta(days=3),
                is_active=False,
            )
        )
    db.commit()

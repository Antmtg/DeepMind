from sqlalchemy import select

from conftest import login

from app.core.device_keys import hash_device_key
from app.database.session import SessionLocal
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.user import User


def _patient(db):
    return db.scalar(
        select(User).where(User.role == "athlete").order_by(User.id)
    )


def _seed_device(
    db,
    device_id="ESP32-TEST-01",
    api_key="test-api-key-012345678",
    mac_address="AA:BB:CC:DD:EE:99",
    user_id=None,
):
    """Crea un dispositivo de prueba en la BD si no existe."""
    device = db.scalar(select(Device).where(Device.device_id == device_id))
    if device is None:
        if user_id is None:
            patient = _patient(db)
            user_id = patient.id if patient else None
        device = Device(
            device_id=device_id,
            name="ESP32 Prueba",
            location="Laboratorio",
            mac_address=mac_address,
            api_key=hash_device_key(api_key),
            is_active=True,
            user_id=user_id,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
    return device


def test_dispositivos_listado_requiere_login(client):
    response = client.get("/api/devices")
    assert response.status_code == 401


def test_dispositivos_listado_autenticado(client):
    assert login(client, "deportista.deepmind.demo@gmail.com").status_code == 200
    with SessionLocal() as db:
        _seed_device(db)

    response = client.get("/api/devices")
    assert response.status_code == 200
    datos = response.json()
    ids = [d["device_id"] for d in datos]
    assert "ESP32-TEST-01" in ids


def test_dispositivos_no_exponen_api_key(client):
    assert login(client, "deportista.deepmind.demo@gmail.com").status_code == 200
    response = client.get("/api/devices")
    assert response.status_code == 200
    for device in response.json():
        assert "api_key" not in device
        assert "owner_name" in device


def test_ingest_medicion_esp32(client):
    api_key = "test-api-key-012345678"
    with SessionLocal() as db:
        device = _seed_device(db, api_key=api_key)

    # Sin api_key -> 401
    response = client.post(
        "/api/devices/ingest",
        json={"spo2": 96},
    )
    assert response.status_code == 401

    # Con api_key invalida -> 401
    response = client.post(
        "/api/devices/ingest",
        json={"spo2": 96},
        headers={"X-Device-Api-Key": "clave-invalida"},
    )
    assert response.status_code == 401

    # Con api_key valida -> 201 y guarda heart_rate_bpm
    response = client.post(
        "/api/devices/ingest",
        json={"spo2": 96, "heart_rate_bpm": 78},
        headers={"X-Device-Api-Key": api_key},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["spo2"] == 96
    assert data["heart_rate_bpm"] == 78
    assert data["device_id"] == device.device_id


def test_heartbeat_actualiza_ultimo_contacto(client):
    api_key = "test-api-key-012345678"
    with SessionLocal() as db:
        device = _seed_device(db, api_key=api_key)

    response = client.post(
        f"/api/devices/{device.id}/heartbeat",
        headers={"X-Device-Api-Key": api_key},
    )
    assert response.status_code == 200
    assert response.json()["last_seen"] is not None


def test_mediciones_del_dispositivo(client):
    assert login(client, "deportista.deepmind.demo@gmail.com").status_code == 200
    with SessionLocal() as db:
        device = _seed_device(
            db,
            device_id="ESP32-TEST-MED",
            api_key="test-api-key-med-0001",
            mac_address="AA:BB:CC:DD:EE:98",
        )
        device_id_db = device.id
        db.add(
            Measurement(
                user_id=device.user_id,
                device_id=device_id_db,
                spo2=95,
                heart_rate_bpm=80,
                source="esp32",
            )
        )
        db.commit()

    response = client.get(f"/api/devices/{device_id_db}/measurements")
    assert response.status_code == 200
    datos = response.json()
    assert len(datos) == 1
    assert datos[0]["spo2"] == 95
    assert datos[0]["heart_rate_bpm"] == 80


def test_paciente_no_puede_leer_dispositivo_ajeno(client):
    with SessionLocal() as db:
        other = db.scalar(
            select(User).where(User.email == "paciente.ajeno@example.com")
        )
        if other is None:
            from app.core.security import hash_password

            other = User(
                full_name="Paciente Ajeno",
                email="paciente.ajeno@example.com",
                password_hash=hash_password("Practica4!"),
                role="athlete",
            )
            db.add(other)
            db.commit()
            db.refresh(other)
        device = _seed_device(
            db,
            device_id="ESP32-TEST-AJENO",
            api_key="test-api-key-ajeno-01",
            mac_address="AA:BB:CC:DD:EE:96",
            user_id=other.id,
        )
        device_id_db = device.id

    assert login(client, "deportista.deepmind.demo@gmail.com").status_code == 200
    assert client.get(f"/api/devices/{device_id_db}").status_code == 403
    assert client.get(f"/api/devices/{device_id_db}/measurements").status_code == 403
    assert (
        client.get(f"/api/devices/{device_id_db}/latest-measurement").status_code
        == 403
    )


def test_especialista_puede_leer_dispositivo_de_su_paciente(client):
    with SessionLocal() as db:
        device = db.scalar(
            select(Device).where(Device.device_id == "ESP32-DM-01")
        )
        device_id_db = device.id

    assert login(client, "entrenador.deepmind.demo@gmail.com").status_code == 200
    assert client.get(f"/api/devices/{device_id_db}").status_code == 200


def test_cuidador_no_puede_editar_dispositivos(client):
    with SessionLocal() as db:
        device = db.scalar(
            select(Device).where(Device.device_id == "ESP32-DM-01")
        )
        device_id_db = device.id

    assert login(client, "entrenador.deepmind.demo@gmail.com").status_code == 200
    response = client.patch(
        f"/api/devices/{device_id_db}",
        json={"name": "Cambio no permitido"},
    )
    assert response.status_code == 403

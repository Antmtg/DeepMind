import re
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from conftest import login

from app.core.config import get_settings
from app.core.device_keys import hash_device_key
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.user import User


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _ensure_user(db, *, role: str = "athlete") -> User:
    email = f"{_unique('usuario')}@example.com"
    user = User(
        full_name=f"Usuario {email}",
        email=email,
        password_hash=hash_password("Practica4!"),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _device(db, device_id: str) -> Device | None:
    return db.scalar(select(Device).where(Device.device_id == device_id))


def _provision(client, *, device_id: str | None = None, **extra):
    settings = get_settings()
    payload = {"device_id": device_id or _unique("ESP32-TEST")}
    payload.update(extra)
    return client.post(
        "/api/devices/provision",
        json=payload,
        headers={"X-Provisioning-Key": settings.device_provisioning_key},
    )


def _login_new_user(client, *, role: str = "athlete") -> User:
    with SessionLocal() as db:
        user = _ensure_user(db, role=role)
        email = user.email
    assert login(client, email).status_code == 200
    return user


@pytest.fixture()
def device_settings(monkeypatch):
    """Amplía la capacidad para que las pruebas no choquen con el seed."""
    settings = get_settings()
    monkeypatch.setattr(settings, "max_devices", 50)
    monkeypatch.setattr(settings, "max_devices_per_user", 1)
    monkeypatch.setattr(settings, "pairing_max_attempts", 10)
    monkeypatch.setattr(settings, "pairing_attempt_window_seconds", 60)
    return settings


def test_provision_requiere_clave(client, device_settings):
    payload = {"device_id": _unique("ESP32-NOKEY")}
    assert client.post("/api/devices/provision", json=payload).status_code == 401
    assert (
        client.post(
            "/api/devices/provision",
            json=payload,
            headers={"X-Provisioning-Key": "clave-incorrecta"},
        ).status_code
        == 401
    )


def test_provision_crea_dispositivo_pendiente(client, device_settings):
    device_id = _unique("ESP32-PROV")
    response = _provision(client, device_id=device_id)

    assert response.status_code == 201
    data = response.json()
    assert data["device_id"] == device_id
    assert len(data["api_key"]) >= 32
    assert re.fullmatch(r"\d{6}", data["pairing_code"])
    assert data["pairing_expires_at"]
    assert data["max_devices"] == device_settings.max_devices
    assert data["registered_devices"] >= 1

    with SessionLocal() as db:
        device = _device(db, device_id)
        assert device is not None
        assert device.user_id is None
        assert device.is_active is True
        assert device.api_key != data["api_key"]
        assert device.api_key == hash_device_key(data["api_key"])
        assert device.pairing_code_hash is not None
        assert device.pairing_code_hash != data["pairing_code"]
        assert len(device.pairing_code_hash) == 64


def test_provision_rota_clave_de_dispositivo_no_vinculado(client, device_settings):
    device_id = _unique("ESP32-REUSE")
    first = _provision(client, device_id=device_id)
    second = _provision(client, device_id=device_id)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["api_key"] != second.json()["api_key"]
    assert second.json()["device_id"] == device_id

    # La credencial anterior deja de autenticar; la nueva sí se reconoce,
    # aunque la ingesta se rechaza hasta que el usuario vincule el equipo.
    old_key = first.json()["api_key"]
    assert (
        client.post(
            "/api/devices/ingest",
            json={"spo2": 97},
            headers={"X-Device-Api-Key": old_key},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/devices/ingest",
            json={"spo2": 97},
            headers={"X-Device-Api-Key": second.json()["api_key"]},
        ).status_code
        == 409
    )


def test_provision_rechaza_dispositivo_ya_vinculado(client, device_settings):
    _login_new_user(client)
    device_id = _unique("ESP32-CLAIMED")
    response = client.post(
        "/api/devices/self-register",
        json={"device_id": device_id, "name": "Sensor ya vinculado"},
    )
    assert response.status_code == 201

    response = _provision(client, device_id=device_id)
    assert response.status_code == 409
    assert "vinculado" in response.json()["detail"]


def test_pair_vincula_y_permite_ingesta(client, device_settings):
    user = _login_new_user(client)
    device_id = _unique("ESP32-PAIR")
    provision = _provision(client, device_id=device_id).json()

    response = client.post(
        "/api/devices/pair",
        json={"pairing_code": provision["pairing_code"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == device_id
    assert data["user_id"] == user.id
    assert data["is_paired"] is True
    assert data["owner_name"] == user.full_name

    with SessionLocal() as db:
        device = _device(db, device_id)
        assert device.user_id == user.id
        assert device.pairing_code_hash is None
        assert device.pairing_expires_at is None

    listed = client.get("/api/devices").json()
    assert any(item["device_id"] == device_id for item in listed)

    ingest = client.post(
        "/api/devices/ingest",
        json={"spo2": 97, "heart_rate_bpm": 70},
        headers={"X-Device-Api-Key": provision["api_key"]},
    )
    assert ingest.status_code == 201

    with SessionLocal() as db:
        device = _device(db, device_id)
        assert device.last_seen is not None


def test_pair_rechaza_ingesta_antes_de_vincular(client, device_settings):
    user = _login_new_user(client)
    device_id = _unique("ESP32-HISTORY")
    provision = _provision(client, device_id=device_id).json()

    ingest = client.post(
        "/api/devices/ingest",
        json={"spo2": 96},
        headers={"X-Device-Api-Key": provision["api_key"]},
    )
    assert ingest.status_code == 409
    assert "vinculado" in ingest.json()["detail"]

    response = client.post(
        "/api/devices/pair",
        json={"pairing_code": provision["pairing_code"]},
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        device = _device(db, device_id)
        measurements = db.scalars(
            select(Measurement).where(Measurement.device_id == device.id)
        ).all()
        assert measurements == []

    # Ya vinculado, la misma credencial sí puede registrar lecturas.
    ingest = client.post(
        "/api/devices/ingest",
        json={"spo2": 96},
        headers={"X-Device-Api-Key": provision["api_key"]},
    )
    assert ingest.status_code == 201


def test_pair_rechaza_codigo_invalido_y_vencido(client, device_settings):
    _login_new_user(client)

    assert (
        client.post(
            "/api/devices/pair",
            json={"pairing_code": "abcdef"},
        ).status_code
        == 400
    )

    device_id = _unique("ESP32-EXPIRED")
    provision = _provision(client, device_id=device_id).json()
    with SessionLocal() as db:
        device = _device(db, device_id)
        device.pairing_expires_at = datetime.now().astimezone() - timedelta(
            minutes=1
        )
        db.add(device)
        db.commit()

    response = client.post(
        "/api/devices/pair",
        json={"pairing_code": provision["pairing_code"]},
    )
    assert response.status_code == 400
    with SessionLocal() as db:
        device = _device(db, device_id)
        assert device.pairing_code_hash is None


def test_pair_rechaza_dispositivo_desactivado(client, device_settings):
    _login_new_user(client)
    device_id = _unique("ESP32-INACTIVE")
    provision = _provision(client, device_id=device_id).json()
    with SessionLocal() as db:
        device = _device(db, device_id)
        device.is_active = False
        db.add(device)
        db.commit()

    response = client.post(
        "/api/devices/pair",
        json={"pairing_code": provision["pairing_code"]},
    )
    assert response.status_code == 403


def test_pair_no_permite_reutilizar_codigo(client, device_settings):
    _login_new_user(client)
    device_id = _unique("ESP32-ONCE")
    provision = _provision(client, device_id=device_id).json()

    first = client.post(
        "/api/devices/pair",
        json={"pairing_code": provision["pairing_code"]},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/devices/pair",
        json={"pairing_code": provision["pairing_code"]},
    )
    assert second.status_code == 400


def test_pair_requiere_login(client, device_settings):
    assert (
        client.post(
            "/api/devices/pair",
            json={"pairing_code": "123456"},
        ).status_code
        == 401
    )


def test_pair_respeta_un_dispositivo_por_usuario(client, device_settings):
    _login_new_user(client)
    assert (
        client.post(
            "/api/devices/self-register",
            json={"name": "Mi primer sensor"},
        ).status_code
        == 201
    )

    device_id = _unique("ESP32-SECOND")
    provision = _provision(client, device_id=device_id).json()
    response = client.post(
        "/api/devices/pair",
        json={"pairing_code": provision["pairing_code"]},
    )
    assert response.status_code == 409
    assert "Cada cuenta" in response.json()["detail"]


def test_pair_limita_intentos_por_minuto(client, device_settings):
    device_settings.pairing_max_attempts = 2
    _login_new_user(client)

    assert (
        client.post(
            "/api/devices/pair", json={"pairing_code": "abcdef"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/devices/pair", json={"pairing_code": "abcdef"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/devices/pair", json={"pairing_code": "abcdef"}
        ).status_code
        == 429
    )


def test_registro_manual_devuelve_credenciales_una_vez(client, device_settings):
    assert client.post("/api/devices/self-register", json={}).status_code == 401

    user = _login_new_user(client)
    response = client.post(
        "/api/devices/self-register",
        json={"name": "Sensor manual", "location": "Sala"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["api_key"]
    assert data["device"]["user_id"] == user.id
    assert data["device"]["is_paired"] is True
    assert data["device"]["name"] == "Sensor manual"
    assert data["device"]["location"] == "Sala"

    listed = client.get("/api/devices").json()
    assert all("api_key" not in item for item in listed)
    assert any(item["device_id"] == data["device"]["device_id"] for item in listed)

    second = client.post(
        "/api/devices/self-register",
        json={"name": "Otro sensor"},
    )
    assert second.status_code == 409
    assert "Cada cuenta" in second.json()["detail"]


def test_registro_manual_rechaza_device_id_duplicado(client, device_settings):
    _login_new_user(client)
    device_id = _unique("ESP32-DUP")
    first = client.post(
        "/api/devices/self-register",
        json={"device_id": device_id, "name": "Primero"},
    )
    assert first.status_code == 201

    _login_new_user(client)
    second = client.post(
        "/api/devices/self-register",
        json={"device_id": device_id, "name": "Duplicado"},
    )
    assert second.status_code == 409
    assert "Ya existe" in second.json()["detail"]


def test_propietario_edita_solo_nombre_y_ubicacion(client, device_settings):
    _login_new_user(client)
    created = client.post(
        "/api/devices/self-register",
        json={"name": "Sensor original", "location": "Sala"},
    ).json()
    device_id = created["device"]["id"]

    response = client.patch(
        f"/api/devices/{device_id}",
        json={"name": "Sensor renombrado", "location": "Dormitorio"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Sensor renombrado"
    assert response.json()["location"] == "Dormitorio"

    forbidden = client.patch(
        f"/api/devices/{device_id}",
        json={"is_active": False},
    )
    assert forbidden.status_code == 403


def test_rotar_api_key_invalida_la_anterior(client, device_settings):
    _login_new_user(client)
    created = client.post(
        "/api/devices/self-register",
        json={"name": "Sensor rotación"},
    ).json()
    device_id = created["device"]["id"]
    old_key = created["api_key"]

    response = client.post(f"/api/devices/{device_id}/rotate-key")
    assert response.status_code == 200
    new_key = response.json()["api_key"]
    assert new_key != old_key

    assert (
        client.post(
            "/api/devices/ingest",
            json={"spo2": 97},
            headers={"X-Device-Api-Key": old_key},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/devices/ingest",
            json={"spo2": 97},
            headers={"X-Device-Api-Key": new_key},
        ).status_code
        == 201
    )


def test_otro_paciente_no_puede_rotar_ni_desvincular(client, device_settings):
    _login_new_user(client)
    created = client.post(
        "/api/devices/self-register",
        json={"name": "Sensor privado"},
    ).json()
    device_id = created["device"]["id"]

    _login_new_user(client)
    assert client.post(f"/api/devices/{device_id}/rotate-key").status_code == 403
    assert client.post(f"/api/devices/{device_id}/unpair").status_code == 403


def test_desvincular_conserva_historial_y_desactiva(client, device_settings):
    _login_new_user(client)
    created = client.post(
        "/api/devices/self-register",
        json={"name": "Sensor a desvincular"},
    ).json()
    device_id = created["device"]["id"]
    api_key = created["api_key"]

    response = client.post(f"/api/devices/{device_id}/unpair")
    assert response.status_code == 204

    with SessionLocal() as db:
        device = db.get(Device, device_id)
        assert device.user_id is None
        assert device.is_active is False
        assert device.api_key != api_key

    assert client.get(f"/api/devices/{device_id}").status_code == 403
    # La clave anterior queda invalidada, no solo desactivada.
    assert (
        client.post(
            "/api/devices/ingest",
            json={"spo2": 97},
            headers={"X-Device-Api-Key": api_key},
        ).status_code
        == 401
    )


def test_heartbeat_simple_por_api_key(client, device_settings):
    device_id = _unique("ESP32-HB")
    provision = _provision(client, device_id=device_id).json()

    response = client.post(
        "/api/devices/heartbeat",
        headers={"X-Device-Api-Key": provision["api_key"]},
    )
    assert response.status_code == 200
    assert response.json()["device_id"] == device_id
    assert response.json()["last_seen"]

    assert (
        client.post(
            "/api/devices/heartbeat",
            headers={"X-Device-Api-Key": "clave-invalida"},
        ).status_code
        == 401
    )


def test_capacidad_del_servidor(client, device_settings):
    assert client.get("/api/devices/capacity").status_code == 401

    _login_new_user(client)
    response = client.get("/api/devices/capacity")
    assert response.status_code == 200
    data = response.json()
    assert data["max_devices"] == device_settings.max_devices
    assert data["max_devices_per_user"] == 1
    assert data["registered_devices"] >= 1
    assert data["available_slots"] == max(
        0, data["max_devices"] - data["registered_devices"]
    )
    assert data["can_register"] is True

    client.post("/api/devices/self-register", json={"name": "Mi sensor"})
    data = client.get("/api/devices/capacity").json()
    assert data["user_devices"] == 1
    assert data["can_register"] is False


def test_limite_global_de_dispositivos(client, device_settings, monkeypatch):
    with SessionLocal() as db:
        registered = int(db.scalar(select(func.count(Device.id))) or 0)
    monkeypatch.setattr(device_settings, "max_devices", registered)

    response = _provision(client, device_id=_unique("ESP32-FULL"))
    assert response.status_code == 409
    assert "máximo" in response.json()["detail"]

    _login_new_user(client)
    response = client.post(
        "/api/devices/self-register",
        json={"name": "Sensor sin cupo"},
    )
    assert response.status_code == 409

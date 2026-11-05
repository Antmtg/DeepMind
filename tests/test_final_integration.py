"""Pruebas del recorrido final: dos dispositivos, separación y trazabilidad."""

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


def _create_user(*, role: str = "athlete") -> User:
    email = f"{_unique('final')}@example.com"
    with SessionLocal() as db:
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


@pytest.fixture()
def capacity(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "max_devices", 100)
    monkeypatch.setattr(settings, "max_devices_per_user", 1)
    return settings


def _register_device(client, name: str) -> dict:
    response = client.post(
        "/api/devices/self-register",
        json={"name": name, "location": "Laboratorio"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _ingest(client, api_key: str, **values):
    payload = {
        "spo2": values.get("spo2", 97),
        "heart_rate_bpm": values.get("heart_rate_bpm", 72),
        "source": values.get("source", "esp32"),
    }
    return client.post(
        "/api/devices/ingest",
        json=payload,
        headers={"X-Device-Api-Key": api_key},
    )


def test_dos_usuarios_y_dos_dispositivos_reciben_datos_separados(client, capacity):
    user_a = _create_user()
    user_b = _create_user()

    assert login(client, user_a.email).status_code == 200
    device_a = _register_device(client, "ESP32 Usuario A")

    assert login(client, user_b.email).status_code == 200
    device_b = _register_device(client, "ESP32 Usuario B")

    # Los dos equipos envían durante el mismo periodo, con claves distintas.
    response_a = _ingest(client, device_a["api_key"], spo2=98, heart_rate_bpm=70)
    response_b = _ingest(client, device_b["api_key"], spo2=93, heart_rate_bpm=95)
    assert response_a.status_code == 201
    assert response_b.status_code == 201
    assert response_a.json()["device_id"] == device_a["device"]["device_id"]
    assert response_b.json()["device_id"] == device_b["device"]["device_id"]

    with SessionLocal() as db:
        rows = db.scalars(
            select(Measurement).where(
                Measurement.device_id.in_(
                    [device_a["device"]["id"], device_b["device"]["id"]]
                )
            )
        ).all()
        by_device = {row.device_id: row for row in rows}
        assert by_device[device_a["device"]["id"]].user_id == user_a.id
        assert by_device[device_b["device"]["id"]].user_id == user_b.id

    assert login(client, user_a.email).status_code == 200
    latest_a = client.get(
        f"/api/devices/{device_a['device']['id']}/latest-measurement"
    )
    assert latest_a.status_code == 200
    assert latest_a.json()["spo2"] == 98
    assert latest_a.json()["device_id"] == device_a["device"]["device_id"]

    # A no puede consultar el dispositivo de B; el servidor responde 403.
    assert (
        client.get(f"/api/devices/{device_b['device']['id']}/measurements").status_code
        == 403
    )


def test_reasignar_dispositivo_no_expone_historial_ajeno(client, capacity):
    user_a = _create_user()
    user_b = _create_user()

    assert login(client, user_a.email).status_code == 200
    created = _register_device(client, "ESP32 reasignable")
    device_pk = created["device"]["id"]
    assert _ingest(client, created["api_key"], spo2=91).status_code == 201

    assert client.post(f"/api/devices/{device_pk}/unpair").status_code == 204

    # El equipo vuelve a aprovisionarse y se vincula a B con una clave nueva.
    provision = client.post(
        "/api/devices/provision",
        json={"device_id": created["device"]["device_id"]},
        headers={"X-Provisioning-Key": capacity.device_provisioning_key},
    )
    assert provision.status_code == 201, provision.text
    new_key = provision.json()["api_key"]
    assert new_key != created["api_key"]

    assert login(client, user_b.email).status_code == 200
    pair = client.post(
        "/api/devices/pair",
        json={"pairing_code": provision.json()["pairing_code"]},
    )
    assert pair.status_code == 200

    assert _ingest(client, new_key, spo2=99).status_code == 201

    history = client.get(f"/api/devices/{device_pk}/measurements")
    assert history.status_code == 200
    rows = history.json()
    assert len(rows) == 1
    assert rows[0]["spo2"] == 99
    assert rows[0]["user_id"] == user_b.id

    with SessionLocal() as db:
        old_owner_rows = db.scalar(
            select(func.count(Measurement.id)).where(
                Measurement.device_id == device_pk,
                Measurement.user_id == user_a.id,
            )
        )
        assert old_owner_rows == 1


def test_ingesta_sin_vincular_y_credencial_invalida_quedan_auditadas(
    client, capacity
):
    device_id = _unique("ESP32-SIN-DUENO")
    provision = client.post(
        "/api/devices/provision",
        json={"device_id": device_id},
        headers={"X-Provisioning-Key": capacity.device_provisioning_key},
    )
    assert provision.status_code == 201

    rejected = _ingest(client, provision.json()["api_key"])
    assert rejected.status_code == 409
    assert "vinculado" in rejected.json()["detail"]

    unauthorized = _ingest(client, "clave-que-no-existe")
    assert unauthorized.status_code == 401

    assert login(client, "admin.deepmind.demo@gmail.com").status_code == 200
    by_action = client.get("/api/audit?action=DEVICE_AUTH_FAILED&limit=200").json()
    assert any("Credencial de dispositivo rechazada" in event["detail"] for event in by_action)
    rejected_events = client.get(
        "/api/audit?action=DEVICE_DATA_REJECTED&limit=200"
    ).json()
    assert any(device_id in event["detail"] for event in rejected_events)


def test_payload_invalido_no_se_guarda_y_queda_auditado(client, capacity):
    user = _create_user()
    assert login(client, user.email).status_code == 200
    created = _register_device(client, "ESP32 validación")

    response = _ingest(client, created["api_key"], spo2=150, temperature_c=80)
    assert response.status_code == 422

    with SessionLocal() as db:
        count = db.scalar(
            select(func.count(Measurement.id)).where(
                Measurement.device_id == created["device"]["id"]
            )
        )
        assert count == 0

    assert login(client, "admin.deepmind.demo@gmail.com").status_code == 200
    events = client.get("/api/audit?action=DEVICE_DATA_REJECTED&limit=200").json()
    assert any("Payload inválido" in event["detail"] for event in events)


def test_logout_cierra_la_sesion_del_navegador(client):
    assert login(client, "deportista.deepmind.demo@gmail.com").status_code == 200
    assert client.get("/api/dashboard").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/dashboard").status_code == 401


def test_api_key_no_se_guarda_en_texto_plano(client, capacity):
    user = _create_user()
    assert login(client, user.email).status_code == 200
    created = _register_device(client, "ESP32 hash")
    plain = created["api_key"]

    with SessionLocal() as db:
        device = db.get(Device, created["device"]["id"])
        assert device.api_key != plain
        assert device.api_key == hash_device_key(plain)
        assert len(device.api_key) == 64

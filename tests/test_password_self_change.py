"""Pruebas del cambio de contraseña por la propia usuaria.

Flujo real del proyecto: nosotros entregamos una contraseña primaria en
persona; cada usuaria entra y la reemplaza por una propia desde su cuenta.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from conftest import login  # noqa: E402

from fastapi.testclient import TestClient

ADMIN = "admin.deepmind.demo@gmail.com"


def crear_cuenta(client: TestClient, correo: str, primaria: str = "Primaria1A"):
    resp = login(client, ADMIN)
    assert resp.status_code == 200, f"login admin: {resp.text} ({resp.status_code})"
    resp = client.post(
        "/api/users",
        json={
            "full_name": "Areli Orozco",
            "email": correo,
            "role": "athlete",
            "password": primaria,
        },
    )
    assert resp.status_code == 201, resp.text
    # Deja la sesión de la usuaria activa para el cambio.
    resp = client.post("/api/auth/login", json={"email": correo, "password": primaria})
    assert resp.status_code == 200, f"login usuaria: {resp.text} ({resp.status_code})"
    return resp.json()["user"]["id"]


def test_cambio_exitoso(client):
    crear_cuenta(client, "cambio.ok1@alumnos.udg.mx")
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "Primaria1A", "new_password": "MiNuevaClave1"},
    )
    assert resp.status_code == 200, resp.text

    vieja = client.post(
        "/api/auth/login",
        json={"email": "cambio.ok1@alumnos.udg.mx", "password": "Primaria1A"},
    )
    nueva = client.post(
        "/api/auth/login",
        json={"email": "cambio.ok1@alumnos.udg.mx", "password": "MiNuevaClave1"},
    )
    assert vieja.status_code == 401
    assert nueva.status_code == 200


def test_contraseína_actual_incorrecta(client):
    crear_cuenta(client, "cambio.bad2@alumnos.udg.mx")
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "Incorrecta9", "new_password": "MiNuevaClave1"},
    )
    assert resp.status_code == 401
    # La primaria sigue funcionando.
    ok = client.post(
        "/api/auth/login",
        json={"email": "cambio.bad2@alumnos.udg.mx", "password": "Primaria1A"},
    )
    assert ok.status_code == 200


def test_contrasena_nueva_debil(client):
    crear_cuenta(client, "cambio.deb3@alumnos.udg.mx")
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "Primaria1A", "new_password": "12345678"},
    )
    assert resp.status_code == 422
    ok = client.post(
        "/api/auth/login",
        json={"email": "cambio.deb3@alumnos.udg.mx", "password": "Primaria1A"},
    )
    assert ok.status_code == 200


def test_la_nueva_igual_a_la_actual_rechazada(client):
    crear_cuenta(client, "cambio.igu4@alumnos.udg.mx")
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "Primaria1A", "new_password": "Primaria1A"},
    )
    assert resp.status_code == 422


def test_sin_sesion_rechazado(client):
    client.get("/api/auth/logout")
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "Primaria1A", "new_password": "MiNuevaClave1"},
    )
    assert resp.status_code == 401

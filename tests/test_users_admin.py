"""Pruebas del alta y gestión administrativa de usuarios.

Escenario real del proyecto: el administrador crea las cuentas con el correo
del estudiante y asigna la contraseña en persona. No hay autoregistro.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from conftest import login  # noqa: E402

ADMIN = "admin.deepmind.demo@gmail.com"
PACIENTE = "deportista.deepmind.demo@gmail.com"


def _nueva_cuenta(client, full_name="Estudiante Prueba", email=None, password="ClaveSegura1", role="athlete"):
    return client.post(
        "/api/users",
        json={
            "full_name": full_name,
            "email": email or "estudiante.prueba@alumnos.udg.mx",
            "role": role,
            "password": password,
        },
    )


def test_admin_crea_cuenta_y_el_usuario_puede_iniciar(client):
    assert login(client, ADMIN).status_code == 200

    resp = _nueva_cuenta(client, "Areli Orozco", "areli.test1@alumnos.udg.mx")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "areli.test1@alumnos.udg.mx"
    assert body["role"] == "athlete"
    assert "password" not in body and "password_hash" not in body

    # La contraseña asignada funciona inmediatamente.
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "areli.test1@alumnos.udg.mx", "password": "ClaveSegura1"},
    )
    assert login_resp.status_code == 200


def test_correo_duplicado_rechazado(client):
    assert login(client, ADMIN).status_code == 200
    resp = _nueva_cuenta(client, "Otra Cuenta", PACIENTE)
    assert resp.status_code == 409


def test_password_debil_rechazada(client):
    assert login(client, ADMIN).status_code == 200
    corta = _nueva_cuenta(client, "Caso Uno", "c001@alumnos.udg.mx", password="Aa1")
    assert corta.status_code == 422

    sin_numero = _nueva_cuenta(client, "Caso Dos", "c002@alumnos.udg.mx", password="sin_numeros")
    assert sin_numero.status_code == 422

    con_usuario = _nueva_cuenta(
        client, "Caso Tres", "estudiante4@alumnos.udg.mx", password="estudiante417"
    )
    assert con_usuario.status_code == 422


def test_rol_invalido_rechazado(client):
    assert login(client, ADMIN).status_code == 200
    resp = _nueva_cuenta(client, "Caso Rol", "c003@alumnos.udg.mx", role="jefe")
    assert resp.status_code == 422


def test_no_admin_no_puede_crear_cuentas(client):
    assert login(client, PACIENTE).status_code == 200
    resp = _nueva_cuenta(client, "Intento Ajeno", "c004@alumnos.udg.mx")
    assert resp.status_code == 403


def test_reset_password_commute(client):
    assert login(client, ADMIN).status_code == 200
    creado = _nueva_cuenta(client, "Leonela Gutierrez", "leonela.test2@alumnos.udg.mx")
    user_id = creado.json()["id"]

    reset = client.patch(f"/api/users/{user_id}", json={"password": "NuevaClave42"})
    assert reset.status_code == 200, reset.text

    vieja = client.post(
        "/api/auth/login",
        json={"email": "leonela.test2@alumnos.udg.mx", "password": "ClaveSegura1"},
    )
    nueva = client.post(
        "/api/auth/login",
        json={"email": "leonela.test2@alumnos.udg.mx", "password": "NuevaClave42"},
    )
    assert vieja.status_code == 401
    assert nueva.status_code == 200


def test_reset_password_debil_rechazado(client):
    assert login(client, ADMIN).status_code == 200
    creado = _nueva_cuenta(client, "Anel Sahagun", "anel.test3@alumnos.udg.mx")
    user_id = creado.json()["id"]

    reset = client.patch(f"/api/users/{user_id}", json={"password": "123"})
    assert reset.status_code == 422
    # La contraseña anterior sigue funcionando.
    ok = client.post(
        "/api/auth/login",
        json={"email": "anel.test3@alumnos.udg.mx", "password": "ClaveSegura1"},
    )
    assert ok.status_code == 200


def test_desactivar_cuenta_bloquea_acceso(client):
    assert login(client, ADMIN).status_code == 200
    creado = _nueva_cuenta(client, "Comodin Antonio", "antonio.test4@alumnos.udg.mx")
    user_id = creado.json()["id"]

    patch = client.patch(f"/api/users/{user_id}", json={"is_active": False})
    assert patch.status_code == 200
    assert patch.json()["is_active"] is False

    bloqueado = client.post(
        "/api/auth/login",
        json={"email": "antonio.test4@alumnos.udg.mx", "password": "ClaveSegura1"},
    )
    assert bloqueado.status_code == 401

    # Reactivar la cuenta.
    patch = client.patch(f"/api/users/{user_id}", json={"is_active": True})
    assert patch.status_code == 200
    ok = client.post(
        "/api/auth/login",
        json={"email": "antonio.test4@alumnos.udg.mx", "password": "ClaveSegura1"},
    )
    assert ok.status_code == 200


def test_no_se_puede_desactivar_al_ultimo_admin(client):
    assert login(client, ADMIN).status_code == 200
    admins = [
        u
        for u in client.get("/api/users").json()
        if u["role"] == "admin" and u["is_active"]
    ]
    resp = client.patch(f"/api/users/{admins[0]['id']}", json={"is_active": False})
    assert resp.status_code == 409


def test_cuenta_inexistente_404(client):
    assert login(client, ADMIN).status_code == 200
    resp = client.patch("/api/users/999999", json={"is_active": False})
    assert resp.status_code == 404

from conftest import login


def test_health_is_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_route_requires_login(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 401


def test_valid_login_sets_secure_session_cookie(client):
    response = login(client, "deportista.deepmind.demo@gmail.com")
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "athlete"
    assert "biomonitor_access" in response.cookies
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["user"]["email"] == "deportista.deepmind.demo@gmail.com"


def test_invalid_login_returns_401(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "deportista.deepmind.demo@gmail.com", "password": "Incorrecta!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales incorrectas"


def test_pydantic_rejects_invalid_email(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "esto-no-es-un-correo", "password": "Practica4!"},
    )
    assert response.status_code == 422

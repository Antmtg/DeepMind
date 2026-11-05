import pytest

from conftest import login


@pytest.mark.parametrize(
    ("email", "resource", "expected_status"),
    [
        ("deportista.deepmind.demo@gmail.com", "/api/users", 403),
        ("deportista.deepmind.demo@gmail.com", "/api/audit", 403),
        ("entrenador.deepmind.demo@gmail.com", "/api/users", 403),
        ("entrenador.deepmind.demo@gmail.com", "/api/audit", 403),
        ("admin.deepmind.demo@gmail.com", "/api/users", 200),
        ("admin.deepmind.demo@gmail.com", "/api/audit", 200),
    ],
)
def test_role_permissions(client, email, resource, expected_status):
    assert login(client, email).status_code == 200
    response = client.get(resource)
    assert response.status_code == expected_status


def test_failed_login_is_visible_to_auditor(client):
    client.post(
        "/api/auth/login",
        json={"email": "intruso.biomonitor.demo@gmail.com", "password": "NoValida123!"},
    )
    assert login(client, "admin.deepmind.demo@gmail.com").status_code == 200
    events = client.get("/api/audit").json()
    assert any(
        event["status"] == "DENIED" and event["email_attempted"] == "intruso.biomonitor.demo@gmail.com"
        for event in events
    )

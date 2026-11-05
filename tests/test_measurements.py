from conftest import login


VALID_MEASUREMENT = {
    "spo2": 97,
    "source": "simulator",
}


def test_measurement_requires_login(client):
    response = client.post(
        "/api/measurements",
        json=VALID_MEASUREMENT,
    )
    assert response.status_code == 401


def test_authenticated_user_can_register_measurement(client):
    assert login(
        client,
        "deportista.deepmind.demo@gmail.com",
    ).status_code == 200

    response = client.post(
        "/api/measurements",
        json=VALID_MEASUREMENT,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["spo2"] == 97
    assert data["source"] == "simulator"
    assert isinstance(data["id"], int)
    assert isinstance(data["user_id"], int)
    assert data["measured_at"]


def test_pydantic_rejects_invalid_measurement(client):
    assert login(
        client,
        "deportista.deepmind.demo@gmail.com",
    ).status_code == 200

    response = client.post(
        "/api/measurements",
        json={
            "spo2": 120,
            "source": "simulator",
        },
    )

    assert response.status_code == 422

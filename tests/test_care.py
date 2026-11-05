from datetime import datetime, timezone

from sqlalchemy import select

from conftest import login

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.user import User


def _ensure_user(db, *, email, full_name, role):
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password("Practica4!"),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def test_cuidador_ve_su_paciente_asignado(client):
    assert login(client, "entrenador.deepmind.demo@gmail.com").status_code == 200
    response = client.get("/api/care/patients")
    assert response.status_code == 200
    patients = response.json()
    assert len(patients) >= 1
    assert patients[0]["patient"]["full_name"]
    assert patients[0]["relationship"] == "coach"
    assert patients[0]["device_count"] >= 1
    assert "latest" in patients[0]
    assert isinstance(patients[0]["alerts"], list)


def test_especialista_ve_su_paciente_asignado(client):
    assert login(client, "entrenador.deepmind.demo@gmail.com").status_code == 200
    response = client.get("/api/care/patients")
    assert response.status_code == 200
    patients = response.json()
    assert len(patients) >= 1
    assert patients[0]["relationship"] == "coach"


def test_paciente_no_puede_listar_pacientes_de_cuidado(client):
    assert login(client, "deportista.deepmind.demo@gmail.com").status_code == 200
    assert client.get("/api/care/patients").status_code == 403


def test_cuidador_no_puede_ver_paciente_no_asignado(client):
    with SessionLocal() as db:
        other = _ensure_user(
            db,
            email="paciente.sin.asignacion@example.com",
            full_name="Paciente Sin Asignación",
            role="athlete",
        )
        other_id = other.id

    assert login(client, "entrenador.deepmind.demo@gmail.com").status_code == 200
    response = client.get(f"/api/care/patients/{other_id}")
    assert response.status_code == 403


def test_admin_puede_listar_asignaciones(client):
    assert login(client, "admin.deepmind.demo@gmail.com").status_code == 200
    response = client.get("/api/care/assignments")
    assert response.status_code == 200
    assignments = response.json()
    assert len(assignments) >= 1
    assert all(item["patient"]["full_name"] for item in assignments)
    assert all(item["member"]["full_name"] for item in assignments)


def test_admin_puede_crear_y_desactivar_asignacion(client):
    with SessionLocal() as db:
        patient = _ensure_user(
            db,
            email="paciente.asignacion.nueva@example.com",
            full_name="Paciente Asignación Nueva",
            role="athlete",
        )
        caregiver = _ensure_user(
            db,
            email="cuidador.asignacion.nueva@example.com",
            full_name="Cuidador Asignación Nueva",
            role="coach",
        )
        patient_id = patient.id
        caregiver_id = caregiver.id

    assert login(client, "admin.deepmind.demo@gmail.com").status_code == 200
    response = client.post(
        "/api/care/assignments",
        json={
            "patient_id": patient_id,
            "member_id": caregiver_id,
            "relationship": "coach",
        },
    )
    assert response.status_code == 201
    assignment = response.json()
    assignment_id = assignment["id"]
    assert assignment["is_active"] is True
    created_at = datetime.fromisoformat(assignment["created_at"])
    assert created_at.tzinfo is not None
    assert abs((datetime.now(timezone.utc) - created_at).total_seconds()) < 300

    response = client.delete(f"/api/care/assignments/{assignment_id}")
    assert response.status_code == 204

    response = client.get("/api/care/assignments?include_inactive=true")
    assert response.status_code == 200
    found = [item for item in response.json() if item["id"] == assignment_id]
    assert len(found) == 1
    assert found[0]["is_active"] is False


def test_asignacion_rechaza_vinculo_que_no_coincide(client):
    with SessionLocal() as db:
        patient = _ensure_user(
            db,
            email="paciente.vinculo.invalido@example.com",
            full_name="Paciente Vínculo Inválido",
            role="athlete",
        )
        caregiver = _ensure_user(
            db,
            email="cuidador.vinculo.invalido@example.com",
            full_name="Cuidador Vínculo Inválido",
            role="athlete",
        )
        patient_id = patient.id
        caregiver_id = caregiver.id

    assert login(client, "admin.deepmind.demo@gmail.com").status_code == 200
    response = client.post(
        "/api/care/assignments",
        json={
            "patient_id": patient_id,
            "member_id": caregiver_id,
            "relationship": "athlete",
        },
    )
    assert response.status_code == 422


def test_auditor_filtra_eventos_denegados(client):
    client.post(
        "/api/auth/login",
        json={"email": "intruso.filtro@example.com", "password": "NoValida123!"},
    )
    assert login(client, "admin.deepmind.demo@gmail.com").status_code == 200
    response = client.get("/api/audit?status=DENIED&limit=10")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    assert all(event["status"] == "DENIED" for event in events)

    response = client.get("/api/audit?action=LOGIN&limit=10")
    assert response.status_code == 200
    assert all(event["action"] == "LOGIN" for event in response.json())

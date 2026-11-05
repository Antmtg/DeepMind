import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"
TEST_DB = BACKEND_DIR / "test_biomonitor.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["SECRET_KEY"] = "clave-exclusiva-para-pruebas-automatizadas"

import sys  # noqa: E402

sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def clean_test_database():
    TEST_DB.unlink(missing_ok=True)
    yield
    try:
        from app.database.session import engine

        engine.dispose()
    except Exception:
        pass
    try:
        TEST_DB.unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": "Practica4!"},
    )

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.database.base import Base
from app.database.migrate import migrate
from app.database.seed import (
    seed_demo_assignments,
    seed_demo_devices,
    seed_demo_measurements,
    seed_demo_plans,
    seed_demo_sessions,
    seed_demo_users,
)
from app.database.session import SessionLocal, engine
from app.services.audit_service import register_event
from app import models  # noqa: F401  # Registra los modelos antes de crear tablas.


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate()
    if settings.seed_demo_data:
        with SessionLocal() as db:
            seed_demo_users(db)
            seed_demo_devices(db)
            seed_demo_assignments(db)
            seed_demo_measurements(db)
            seed_demo_sessions(db)
            seed_demo_plans(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.1.5",
    description="Deep Mind Apnea: seguimiento de apnea, sesiones y planes de entrenamiento.",
    lifespan=lifespan,
)
app.include_router(api_router)
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    """Registra payloads inválidos de los ESP32 sin guardar sus valores.

    Pydantic rechaza el cuerpo antes de ejecutar la ruta; por eso la auditoría
    se hace aquí. Solo se anotan los nombres de los campos inválidos.
    """
    if request.url.path.rstrip("/") == "/api/devices/ingest":
        fields = ", ".join(
            ".".join(str(part) for part in error.get("loc", ()) if part != "body")
            for error in exc.errors()
        )
        with SessionLocal() as db:
            register_event(
                db,
                action="DEVICE_DATA_REJECTED",
                status="DENIED",
                detail=f"Payload inválido en ingest. Campos: {fields[:180]}",
                ip_address=request.client.host if request.client else None,
            )
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.get("/api/health", tags=["Sistema"])
def health():
    return {"status": "ok", "service": settings.app_name, "version": "1.1.5"}


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

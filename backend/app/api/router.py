from fastapi import APIRouter

from app.api.routes import audit, auth, care, dashboard, devices, measurements, users


api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(care.router)
api_router.include_router(devices.router)
api_router.include_router(users.router)
api_router.include_router(audit.router)
api_router.include_router(measurements.router)

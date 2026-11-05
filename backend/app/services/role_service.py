from app.models.user import UserRole


ROLE_DASHBOARDS = {
    UserRole.ATHLETE: {
        "title": "Tu apnea, clara y a tu ritmo",
        "description": "Consulta tus mediciones de SpO2 y pulso, tu sensor y el historial de tus intentos.",
        "permissions": [
            "Ver tus mediciones",
            "Consultar tu sensor",
            "Revisar tu historial",
            "Cerrar sesión",
        ],
        "next_module": "Cronómetro de apnea y escala de colores (semáforo)",
    },
    UserRole.COACH: {
        "title": "Acompaña a tus deportistas",
        "description": "Revisa a los deportistas asignados y sus últimas mediciones.",
        "permissions": [
            "Ver deportistas asignados",
            "Consultar sus mediciones",
            "Revisar historial",
            "Cerrar sesión",
        ],
        "next_module": "Seguimiento de sesiones de apnea",
    },
    UserRole.ADMIN: {
        "title": "Administra usuarios, sensores y vínculos",
        "description": "Gestiona el acceso, los dispositivos y las asignaciones.",
        "permissions": [
            "Ver usuarios",
            "Editar y desactivar sensores",
            "Crear y desactivar asignaciones",
            "Cerrar sesión",
        ],
        "next_module": "Auditoría y reportes",
    },
}
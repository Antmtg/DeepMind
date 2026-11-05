from app.models.measurement import Measurement


def measurement_status(measurement: Measurement) -> tuple[str, list[str]]:
    """Devuelve un estado (semáforo) sin alertas textuales.

    El semáforo se usa solo como escala visual: verde/amarillo/rojo.
    No se generan alertas ni mensajes que puedan alterar al deportista.
    """

    status = "normal"

    if measurement.spo2 < 90:
        status = "critical"
    elif measurement.spo2 < 95:
        status = "review"

    heart_rate = measurement.heart_rate_bpm
    if heart_rate is not None:
        if heart_rate < 50 or heart_rate > 120:
            status = "critical"
        elif status != "critical" and (heart_rate < 60 or heart_rate > 100):
            status = "review"

    return status, []


def vitals_from_measurement(measurement: Measurement) -> dict:
    status, _ = measurement_status(measurement)
    return {
        "spo2": measurement.spo2,
        "heart_rate_bpm": measurement.heart_rate_bpm,
        "source": measurement.source,
        "taken_at": measurement.measured_at,
        "status": status,
        "alerts": [],
    }
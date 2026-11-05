"""Limitador de intentos en memoria, suficiente para un servidor casero.

Con varios procesos de uvicorn cada proceso tendría su propio contador. Para
el despliegue previsto (un solo worker y 3-5 ESP32) es suficiente y evita
depender de Redis u otro servicio externo.
"""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic


_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def allow_attempt(key: str, *, limit: int, window_seconds: int) -> bool:
    """Registra un intento y devuelve False si se superó el límite."""
    now = monotonic()
    with _lock:
        bucket = _attempts[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def reset_attempts(key: str) -> None:
    """Limpia el contador tras un intento exitoso."""
    with _lock:
        _attempts.pop(key, None)

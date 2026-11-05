"""Prepara dos dispositivos demo para la demostracion simultanea.

Rota la api_key de dos sensores demo usando una sesion de administrador y
guarda las credenciales nuevas en data/demo_credentials.json. El archivo
contiene secretos y esta ignorado por Git.

Uso:
    python simulator/prepare_demo.py
    python simulator/prepare_demo.py --devices ESP32-O2T-01 ESP32-O2T-02

Requisitos:
    - Servidor FastAPI en marcha (por defecto http://127.0.0.1:8100).
    - Cuenta administradora demo con la contrasena indicada.

El script no imprime las claves en pantalla. Solo escribe el archivo que
despues lee simulator/device_simulator.py.
"""

import argparse
import getpass
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "demo_credentials.json"
DEFAULT_DEVICES = ["ESP32-O2T-01", "ESP32-O2T-02"]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8100")
    parser.add_argument("--admin-email", default="admin.biomonitor.demo@gmail.com")
    parser.add_argument(
        "--admin-password",
        default=os.environ.get("BIOMONITOR_DEMO_PASSWORD"),
        help="Si se omite, se pide por teclado o se usa BIOMONITOR_DEMO_PASSWORD.",
    )
    parser.add_argument("--devices", nargs="+", default=DEFAULT_DEVICES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main():
    args = parse_args()
    password = args.admin_password
    if not password:
        password = getpass.getpass("Contrasena de la cuenta administradora: ")

    with httpx.Client(base_url=args.base_url, timeout=15.0) as client:
        response = client.post(
            "/api/auth/login",
            json={"email": args.admin_email, "password": password},
        )
        if response.status_code != 200:
            raise SystemExit(
                f"No se pudo iniciar sesion: HTTP {response.status_code} "
                f"{response.text[:200]}"
            )

        response = client.get("/api/devices")
        response.raise_for_status()
        devices = response.json()
        by_code = {device["device_id"]: device for device in devices}

        missing = [code for code in args.devices if code not in by_code]
        if missing:
            raise SystemExit(
                "No existen estos dispositivos: " + ", ".join(missing)
            )

        credentials = []
        for code in args.devices:
            device = by_code[code]
            rotated = client.post(f"/api/devices/{device['id']}/rotate-key")
            if rotated.status_code != 200:
                raise SystemExit(
                    f"No se pudo rotar la clave de {code}: "
                    f"HTTP {rotated.status_code} {rotated.text[:200]}"
                )
            data = rotated.json()
            credentials.append(
                {
                    "device_db_id": device["id"],
                    "device_id": device["device_id"],
                    "owner_name": device.get("owner_name"),
                    "api_key": data["api_key"],
                }
            )
            owner = device.get("owner_name") or "sin propietario"
            print(f"Clave rotada: {code} ({owner})")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "server_url": args.base_url.rstrip("/"),
        "devices": credentials,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    try:
        os.chmod(args.output, 0o600)
    except OSError:
        pass

    print("")
    print(f"Credenciales guardadas en {args.output}")
    print("El archivo contiene secretos y no debe incluirse en el ZIP.")
    print("Ahora ejecuta: python simulator/device_simulator.py")


if __name__ == "__main__":
    main()

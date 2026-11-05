"""Simulador de dos ESP32 para la demostracion simultanea.

Envia lecturas MARCADAS COMO SIMULADAS (source="simulator") a dos dispositivos
distintos, cada uno vinculado a un usuario demo diferente. Sirve para mostrar
que el servidor separa los datos por propietario cuando ambos envian a la vez.

Antes de ejecutarlo:
    python simulator/prepare_demo.py

Uso:
    python simulator/device_simulator.py
    python simulator/device_simulator.py --interval 5 --once
    python simulator/device_simulator.py --devices ESP32-O2T-01

El simulador nunca usa source="esp32": la app mostrara "Simulador (datos
simulados)" en cada lectura y en el historial.
"""

import argparse
import json
import random
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CREDENTIALS = ROOT / "data" / "demo_credentials.json"

# Perfiles distintos para que cada paciente vea datos propios y reconocibles.
PROFILES = [
    {
        "spo2": [96.0, 99.0],
        "heart_rate_bpm": [68.0, 78.0],
    },
    {
        "spo2": [93.0, 96.0],
        "heart_rate_bpm": [82.0, 92.0],
    },
]

stop_event = threading.Event()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", type=Path, default=DEFAULT_CREDENTIALS)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--heartbeat", type=float, default=30.0)
    parser.add_argument("--devices", nargs="+", default=None)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


def load_devices(path, selected):
    if not path.exists():
        raise SystemExit(
            f"No existe {path}. Ejecuta primero: python simulator/prepare_demo.py"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    devices = payload.get("devices", [])
    if selected:
        wanted = set(selected)
        devices = [item for item in devices if item.get("device_id") in wanted]
    if not devices:
        raise SystemExit("No hay dispositivos en el archivo de credenciales.")
    for item in devices:
        if not item.get("device_id") or not item.get("api_key"):
            raise SystemExit("Credenciales incompletas: falta device_id o api_key.")
    return payload.get("server_url", "http://127.0.0.1:8100"), devices


def next_value(current, bounds):
    low, high = bounds
    step = (high - low) * 0.06
    value = current + random.uniform(-step, step)
    return max(low, min(high, value))


def build_reading(profile, state):
    state["spo2"] = next_value(state["spo2"], profile["spo2"])
    state["heart_rate_bpm"] = next_value(
        state["heart_rate_bpm"], profile["heart_rate_bpm"]
    )
    return {
        "spo2": int(round(state["spo2"])),
        "heart_rate_bpm": int(round(state["heart_rate_bpm"])),
        "source": "simulator",
    }


def send_ingest(client, api_key, reading):
    return client.post(
        "/api/devices/ingest",
        json=reading,
        headers={"X-Device-Api-Key": api_key},
    )


def send_heartbeat(client, api_key):
    return client.post(
        "/api/devices/heartbeat",
        json={},
        headers={"X-Device-Api-Key": api_key},
    )


def run_device(server_url, device, profile_index, args):
    code = device["device_id"]
    owner = device.get("owner_name") or "sin propietario"
    api_key = device["api_key"]
    profile = PROFILES[profile_index % len(PROFILES)]
    state = {
        "spo2": sum(profile["spo2"]) / 2,
        "heart_rate_bpm": sum(profile["heart_rate_bpm"]) / 2,
    }
    last_heartbeat = 0.0

    with httpx.Client(base_url=server_url, timeout=10.0) as client:
        while not stop_event.is_set():
            reading = build_reading(profile, state)
            started = time.monotonic()
            try:
                response = send_ingest(client, api_key, reading)
            except Exception as error:
                print(f"[{code}] error de red: {error}", flush=True)
            else:
                if response.status_code == 201:
                    stamp = datetime.now().strftime("%H:%M:%S")
                    print(
                        f"[{stamp}] {code} ({owner}): "
                        f"SpO2 {reading['spo2']}% · pulso {reading['heart_rate_bpm']} lpm "
                        f"· source=simulator",
                        flush=True,
                    )
                elif response.status_code in (401, 403):
                    print(
                        f"[{code}] rechazado HTTP {response.status_code}: "
                        f"{response.text[:200]}",
                        flush=True,
                    )
                    print(
                        f"[{code}] rota la clave con prepare_demo.py y vuelve a intentar.",
                        flush=True,
                    )
                    return
                else:
                    print(
                        f"[{code}] HTTP {response.status_code}: {response.text[:200]}",
                        flush=True,
                    )

            now = time.monotonic()
            if now - last_heartbeat >= args.heartbeat:
                try:
                    heartbeat = send_heartbeat(client, api_key)
                    if heartbeat.status_code != 200:
                        print(
                            f"[{code}] heartbeat HTTP {heartbeat.status_code}",
                            flush=True,
                        )
                except Exception as error:
                    print(f"[{code}] error en heartbeat: {error}", flush=True)
                last_heartbeat = now

            if args.once:
                return
            elapsed = time.monotonic() - started
            stop_event.wait(max(0.1, args.interval - elapsed))


def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    server_url, devices = load_devices(args.credentials, args.devices)

    print("Deep Mind - simulador de dispositivos")
    print(f"Servidor: {server_url}")
    print(f"Dispositivos: {', '.join(item['device_id'] for item in devices)}")
    print("Origen de los datos: simulator (no son lecturas reales).")
    print("")

    if args.once:
        for index, device in enumerate(devices):
            run_device(server_url, device, index, args)
        return

    threads = []
    for index, device in enumerate(devices):
        thread = threading.Thread(
            target=run_device,
            args=(server_url, device, index, args),
            name=device["device_id"],
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    def shutdown(_signum=None, _frame=None):
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while any(thread.is_alive() for thread in threads):
            for thread in threads:
                thread.join(timeout=0.5)
    except KeyboardInterrupt:
        stop_event.set()

    for thread in threads:
        thread.join(timeout=2.0)
    print("\nSimulador detenido.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_event.set()
        print("\nSimulador detenido.")
        sys.exit(0)

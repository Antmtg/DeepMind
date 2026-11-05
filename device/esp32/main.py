"""
BioMonitor O2T - Firmware ESP32 (MicroPython / Thonny)

Lee SpO2 y pulso con un MAX30102 y, si esta disponible, temperatura corporal
con un DS18B20. Envia las lecturas al backend con su credencial de dispositivo.

Flujos de conexion:

1. Emparejamiento automatico (recomendado):
   - El ESP32 llama a POST /api/devices/provision con X-Provisioning-Key.
   - El backend devuelve una api_key y un codigo de 6 digitos.
   - El codigo se muestra por el monitor serial.
   - El usuario lo ingresa en BioMonitor > Mis sensores.

2. Registro manual desde la app:
   - El usuario crea el sensor y recibe device_id + api_key.
   - Esas credenciales se graban en config.py.

Configuracion: copia config.example.py como config.py en el ESP32 y completa
WiFi, SERVER_URL y PROVISIONING_KEY. config.py no se entrega en el ZIP.

Seguridad:
- No hay claves reales en este archivo.
- Un fallo de lectura no se convierte en una lectura inventada.
- SIMULATION_MODE debe activarse explicitamente y marca source="simulator".
"""

import time

import network
import urequests as requests

try:
    import ujson as json
except ImportError:
    import json

try:
    import machine
except ImportError:
    machine = None

try:
    import config
    CONFIG_ERROR = None
except ImportError as error:
    config = None
    CONFIG_ERROR = error

try:
    from max30102 import MAX30102
except ImportError:
    MAX30102 = None

try:
    from ds18b20 import DS18B20
except ImportError:
    DS18B20 = None

try:
    from pantalla import inicializar_pantalla
except ImportError:
    inicializar_pantalla = None


# Pantalla global de este equipo (solo el ESP32 de Antonio la tiene).
PANTALLA = None


def actualizar_pantalla(lectura=None, estado=""):
    """Actualiza la pantalla si existe. Nunca interrumpe la medicion."""
    if PANTALLA is None:
        return
    try:
        if lectura is not None:
            PANTALLA.mostrar_datos(
                lectura["spo2"],
                lectura["heart_rate_bpm"],
                estado,
            )
        else:
            PANTALLA.mostrar_mensaje(estado or "Sin lecturas", "espera señal")
    except Exception:
        pass


# --- Red y backend ---------------------------------------------------------

def conectar_wifi(ssid, password, timeout_s=20):
    """Conecta el ESP32 al WiFi. Reintenta hasta agotar el timeout."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando a WiFi...", ssid)
        wlan.connect(ssid, password)
        inicio = time.time()
        while not wlan.isconnected():
            if time.time() - inicio > timeout_s:
                print("No se pudo conectar al WiFi")
                return False
            time.sleep(0.5)
    print("WiFi conectado:", wlan.ifconfig()[0])
    return True


def hardware_device_id():
    """Identificador estable basado en el chip; sirve como device_id."""
    if machine is None:
        return "ESP32-SIN-ID"
    try:
        unique = machine.unique_id()
        return "ESP32-" + "".join("{:02X}".format(byte) for byte in unique)
    except Exception:
        return "ESP32-SIN-ID"


def mac_address():
    try:
        mac = network.WLAN(network.STA_IF).config("mac")
        return ":".join("{:02X}".format(byte) for byte in mac)
    except Exception:
        return None


# --- Credenciales ----------------------------------------------------------

def leer_config():
    """Lee las credenciales guardadas en la flash del ESP32."""
    try:
        with open(config.CONFIG_FILE, "r") as archivo:
            data = json.load(archivo)
        if data.get("device_id") and data.get("api_key"):
            return data["device_id"], data["api_key"]
    except (OSError, ValueError):
        pass
    return None


def guardar_config(device_id, api_key):
    try:
        with open(config.CONFIG_FILE, "w") as archivo:
            json.dump({"device_id": device_id, "api_key": api_key}, archivo)
        print("Credenciales guardadas en", config.CONFIG_FILE)
    except OSError as exc:
        print("No se pudieron guardar las credenciales:", exc)


def solicitar_emparejamiento(device_id, guardadas=None):
    """Pide al backend una api_key y un codigo de emparejamiento."""
    url = config.SERVER_URL + "/api/devices/provision"
    payload = {
        "device_id": device_id,
        "name": "Sensor " + device_id,
        "mac_address": mac_address(),
    }
    headers = {
        "Content-Type": "application/json",
        "X-Provisioning-Key": config.PROVISIONING_KEY,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers)
        status = resp.status_code
        body = resp.text
        resp.close()
    except Exception as exc:
        print("Error de red al aprovisionar:", exc)
        if guardadas is not None:
            print("Usando credenciales guardadas:", guardadas[0])
            return guardadas
        return None

    if status == 201:
        data = json.loads(body)
        guardar_config(data["device_id"], data["api_key"])
        print("")
        print("=" * 44)
        print("CODIGO DE EMPAREJAMIENTO:", data["pairing_code"])
        print("Valido hasta:", data.get("pairing_expires_at", "?"))
        print("Ingresalo en BioMonitor > Mis sensores.")
        print("=" * 44)
        print("")
        actualizar_pantalla(estado="Emparejando")
        try:
            if PANTALLA is not None and data.get("pairing_code"):
                PANTALLA.mostrar_codigo(
                    data["pairing_code"],
                    "vence en " + str(data.get("pairing_ttl", "10 min")),
                )
        except Exception:
            pass
        return data["device_id"], data["api_key"]

    if status == 409:
        if guardadas is not None:
            print("El dispositivo ya esta vinculado. Usando credenciales guardadas.")
            return guardadas
        print("El dispositivo ya esta vinculado a una cuenta.")
        print("Si perdiste las credenciales, pide al administrador que lo")
        print("desvincule y vuelve a encender el ESP32.")
        return None

    print("No se pudo aprovisionar. HTTP", status, body)
    if guardadas is not None:
        print("Usando credenciales guardadas:", guardadas[0])
        return guardadas
    return None


def obtener_credenciales():
    """Modo manual o auto-aprovisionamiento con respaldo en la flash."""
    if config.MANUAL_DEVICE_ID and config.MANUAL_API_KEY:
        print("Modo manual:", config.MANUAL_DEVICE_ID)
        return config.MANUAL_DEVICE_ID, config.MANUAL_API_KEY

    guardadas = leer_config()
    device_id = guardadas[0] if guardadas is not None else hardware_device_id()
    print("Sincronizando credenciales para", device_id)
    return solicitar_emparejamiento(device_id, guardadas)


# --- Sensores --------------------------------------------------------------

def inicializar_sensores(i2c=None):
    """Crea los controladores. Devuelve un dict; puede quedar vacio."""
    sensores = {"max30102": None, "ds18b20": None}
    if machine is None:
        print("Sin modulo machine: no se pueden inicializar sensores.")
        return sensores

    if i2c is None:
        try:
            i2c = machine.I2C(
                0,
                scl=machine.Pin(config.I2C_SCL_PIN),
                sda=machine.Pin(config.I2C_SDA_PIN),
                freq=config.I2C_FREQ,
            )
        except Exception as exc:
            print("No se pudo crear el bus I2C:", exc)

    if MAX30102 is not None and i2c is not None:
        try:
            sensores["max30102"] = MAX30102(i2c, config.MAX30102_ADDRESS)
            print("MAX30102 listo en I2C", hex(config.MAX30102_ADDRESS))
        except Exception as exc:
            print("MAX30102 no disponible:", exc)

    if config.USE_DS18B20 and DS18B20 is not None:
        try:
            ds = DS18B20(machine.Pin(config.DS18B20_PIN))
            if ds.available:
                sensores["ds18b20"] = ds
                print("DS18B20 listo en GPIO", config.DS18B20_PIN)
            else:
                print("DS18B20 no detectado; se usara temperatura del sensor.")
        except Exception as exc:
            print("DS18B20 no disponible:", exc)
    return sensores


def leer_simulado():
    """Datos simulados SOLO si SIMULATION_MODE=True. Se etiquetan como tales."""
    import random

    return {
        "spo2": random.randint(94, 99),
        "heart_rate_bpm": random.randint(60, 90),
        "source": "simulator",
    }


def leer_sensor(sensores=None):
    """Devuelve una lectura valida o None. Nunca inventa valores."""
    if config.SIMULATION_MODE:
        lectura = leer_simulado()
        print("[SIMULADOR] No es una lectura real del MAX30102.")
        return lectura

    sensor = (sensores or {}).get("max30102")
    if sensor is None:
        print("Sin MAX30102: no se envia medicion.")
        return None

    try:
        lectura = sensor.read_measurement(
            window_seconds=config.MEASUREMENT_WINDOW_S,
            sample_hz=config.FIFO_SAMPLE_HZ,
        )
    except Exception as exc:
        print("Error leyendo MAX30102:", exc)
        return None

    if lectura is None:
        print("Lectura no valida (senal insuficiente). No se envia nada.")
        return None

    return {
        "spo2": lectura["spo2"],
        "heart_rate_bpm": lectura["heart_rate_bpm"],
        "source": "esp32",
    }


# --- API -------------------------------------------------------------------

def enviar_medicion(lectura, api_key):
    """Envia una medicion al backend. Devuelve True si tuvo exito."""
    url = config.SERVER_URL + "/api/devices/ingest"
    payload = {
        "spo2": lectura["spo2"],
        "heart_rate_bpm": lectura["heart_rate_bpm"],
        "source": lectura["source"],
    }
    headers = {
        "Content-Type": "application/json",
        "X-Device-Api-Key": api_key,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers)
        status = resp.status_code
        print("Respuesta servidor:", status, resp.text)
        resp.close()
        if status == 403:
            print("El dispositivo fue desactivado, desvinculado o su cuenta esta inactiva.")
            print("Borra", config.CONFIG_FILE, "y reinicia para emparejarlo de nuevo.")
        elif status == 401:
            print("La api_key ya no es valida. Rota la clave en la app.")
        return status == 201
    except Exception as exc:
        print("Error enviando medicion:", exc)
        return False


def enviar_heartbeat(api_key):
    """Notifica al backend que el dispositivo sigue activo."""
    url = config.SERVER_URL + "/api/devices/heartbeat"
    headers = {
        "Content-Type": "application/json",
        "X-Device-Api-Key": api_key,
    }
    try:
        resp = requests.post(url, json={}, headers=headers)
        print("Heartbeat:", resp.status_code)
        resp.close()
    except Exception as exc:
        print("Error en heartbeat:", exc)


# --- Programa principal ----------------------------------------------------

def main():
    global PANTALLA

    print("=== BioMonitor O2T - ESP32 ===")

    if config is None:
        print("Falta config.py:", CONFIG_ERROR)
        print("Copia config.example.py como config.py y completa WiFi y servidor.")
        return

    if not conectar_wifi(
        config.WIFI_SSID, config.WIFI_PASSWORD, config.WIFI_TIMEOUT_S
    ):
        print("Saliendo: sin WiFi")
        return

    if config.SIMULATION_MODE:
        print("ATENCION: SIMULATION_MODE=True. Los datos se marcaran como simulados.")

    # Un solo bus I2C compartido por el MAX30102 y, si existe, la pantalla.
    i2c_equipo = None
    try:
        i2c_equipo = machine.I2C(
            0,
            scl=machine.Pin(config.I2C_SCL_PIN),
            sda=machine.Pin(config.I2C_SDA_PIN),
            freq=config.I2C_FREQ,
        )
    except Exception as exc:
        print("No se pudo crear el bus I2C:", exc)

    if (
        i2c_equipo is not None
        and getattr(config, "USE_PANTALLA", False)
        and inicializar_pantalla is not None
    ):
        PANTALLA = inicializar_pantalla(i2c_equipo, config)

    sensores = inicializar_sensores(i2c_equipo)
    if not config.SIMULATION_MODE and sensores.get("max30102") is None:
        print("No hay MAX30102. El equipo enviara heartbeats, pero no mediciones.")
        print("Revisa el cableado I2C o activa SIMULATION_MODE solo para pruebas.")

    credenciales = obtener_credenciales()
    if credenciales is None:
        print("Sin credenciales. Reinicia el ESP32 o usa el registro manual.")
        actualizar_pantalla(estado="Sin credenciales")
        return

    device_id, api_key = credenciales
    print("Dispositivo:", device_id)
    print("Intervalo de envio:", config.INTERVAL_MS, "ms")

    if config.SENSOR_WARMUP_S:
        print("Estabilizando sensor durante", config.SENSOR_WARMUP_S, "s...")
        time.sleep(config.SENSOR_WARMUP_S)

    ultimo_envio = 0
    ultimo_heartbeat = 0
    primer_ciclo = True

    while True:
        ahora = time.ticks_ms()

        if not network.WLAN(network.STA_IF).isconnected():
            print("WiFi caido, reconectando...")
            conectar_wifi(
                config.WIFI_SSID, config.WIFI_PASSWORD, config.WIFI_TIMEOUT_S
            )

        if primer_ciclo or time.ticks_diff(ahora, ultimo_envio) >= config.INTERVAL_MS:
            primer_ciclo = False
            ultimo_envio = ahora
            lectura = leer_sensor(sensores)
            if lectura is not None:
                print(
                    "Lectura -> SpO2: {}% | Pulso: {} lpm".format(
                        lectura["spo2"],
                        lectura["heart_rate_bpm"],
                    )
                )
                if enviar_medicion(lectura, api_key):
                    actualizar_pantalla(lectura, "Leyendo y enviando")
                else:
                    actualizar_pantalla(lectura, "Sin enlace con servidor")
            else:
                print("Sin lectura valida en este ciclo; no se envia medicion.")
                actualizar_pantalla(None, "Sin señal del sensor")

        if time.ticks_diff(ahora, ultimo_heartbeat) >= config.HEARTBEAT_EVERY_MS:
            enviar_heartbeat(api_key)
            ultimo_heartbeat = ahora

        time.sleep_ms(200)


if __name__ == "__main__":
    main()

# Deep Mind - configuracion del ESP32
#
# Copia este archivo como config.py en el mismo directorio del ESP32 y
# completa los valores. config.py NO se entrega: contiene secretos.
#
# En Thonny: abre config.example.py, guarda una copia como config.py en el
# dispositivo y edita solo esa copia.

# --- Red y servidor ---------------------------------------------------------
WIFI_SSID = "TU_RED_WIFI"
WIFI_PASSWORD = "TU_CONTRASENA_WIFI"

# IP del computador que ejecuta FastAPI, vista desde el ESP32.
# No uses 127.0.0.1: para el ESP32 esa direccion es el propio ESP32.
SERVER_URL = "http://192.168.1.100:8100"

# Debe coincidir con DEVICE_PROVISIONING_KEY del backend (.env).
PROVISIONING_KEY = "cambia-esta-clave-de-provisionamiento"

# --- Identidad --------------------------------------------------------------
# Opcion A (recomendada): dejar vacios y usar emparejamiento automatico.
MANUAL_DEVICE_ID = ""
MANUAL_API_KEY = ""

# Opcion B: credenciales del registro manual desde la app/API.
# MANUAL_DEVICE_ID = "ESP32-O2T-01"
# MANUAL_API_KEY = "pega-aqui-la-api-key"

CONFIG_FILE = "device_config.json"

# --- Hardware I2C (MAX30102) ------------------------------------------------
I2C_SDA_PIN = 21
I2C_SCL_PIN = 22
I2C_FREQ = 400_000
MAX30102_ADDRESS = 0x57

# --- Pantalla monocromatica (solo el ESP32 de Antonio) -----------------------
# Display de un solo color por I2C, 128x64, en la direccion 0x3C.
# Comparte el bus con el MAX30102: GND, VCC, SCL (GPIO 22), SDA (GPIO 21).
# DISPLAY_DRIVER: "ssd1306" estandar; "sh1106" si el chip es SH1106.
USE_PANTALLA = False
DISPLAY_DRIVER = "ssd1306"
DISPLAY_ADDR = 0x3C

# --- Modo de prueba ---------------------------------------------------------
# False = solo envia lecturas reales del sensor.
# True  = envia datos simulados identificados con source="simulator".
# Un fallo de lectura NUNCA se convierte en una lectura inventada.
SIMULATION_MODE = False

# --- Tiempos ----------------------------------------------------------------
INTERVAL_MS = 2_000
HEARTBEAT_EVERY_MS = 60_000
WIFI_TIMEOUT_S = 20
SENSOR_WARMUP_S = 4
FIFO_SAMPLE_HZ = 100
MEASUREMENT_WINDOW_S = 2

# --- Calibracion ------------------------------------------------------------
# La formula SpO2 = 110 - 25 * R es una aproximacion de banco. Ajusta estos
# valores solo con una validacion contra un oximetro de referencia.
SPO2_INTERCEPT = 110.0
SPO2_SLOPE = 25.0

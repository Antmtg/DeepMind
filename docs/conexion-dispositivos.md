# Conexión de dispositivos ESP32

Esta guía cubre el alta, emparejamiento, ingestión, simulación y demostración
simultánea de dos dispositivos. El servidor está pensado para una red local con
**3–5 ESP32 como máximo** y **un dispositivo por cuenta**.

## Reglas de capacidad

| Regla | Valor por defecto | Variable |
|---|---|---|
| Dispositivos registrados en total | 5 | `MAX_DEVICES` |
| Dispositivos por cuenta | 1 | `MAX_DEVICES_PER_USER` |
| Vigencia del código de emparejamiento | 10 minutos | `PAIRING_CODE_TTL_MINUTES` |
| Intentos de código por ventana | 10 | `PAIRING_MAX_ATTEMPTS` |
| Ventana de intentos | 60 segundos | `PAIRING_ATTEMPT_WINDOW_SECONDS` |

La semilla demo crea tres pacientes y reparte un sensor por paciente para
respetar la regla de uno por cuenta.

## Flujo A — Emparejamiento automático

```text
ESP32                         Backend                         Usuario
  |                              |                               |
  |-- POST /devices/provision -->|                               |
  |   X-Provisioning-Key         | crea Device sin dueño         |
  |<-- api_key + código 6 díg. --|                               |
  |                              |                               |
  | muestra el código por serial |                               |
  |                              |<-- POST /devices/pair ---------|
  |                              |    código + sesión             |
  |                              | vincula user_id                |
  |                              |------------------------------>|
  |-- POST /devices/ingest ----->|                               |
  |   X-Device-Api-Key           | guarda medición               |
```

1. El ESP32 llama a `POST /api/devices/provision` con `X-Provisioning-Key`.
2. El backend crea o reutiliza un dispositivo sin propietario, genera una
   `api_key` y un código de 6 dígitos. El código se guarda como HMAC-SHA256 y
   vence a los 10 minutos.
3. El firmware guarda `device_id` + `api_key` en `device_config.json` y muestra
   el código por el monitor serial.
4. El usuario inicia sesión, abre **Mis sensores** y pulsa **Conectar mi
   sensor**. La app consulta los cupos y envía el código a
   `POST /api/devices/pair`.
5. El backend vincula el dispositivo a la cuenta y anula el código.

Si el dispositivo ya está vinculado, `provision` responde `409` y no revela la
`api_key` de otra cuenta. Si el ESP32 perdió sus credenciales, el propietario o
el administrador deben desvincularlo y volver a aprovisionarlo. Después de
desvincular, la clave anterior deja de servir.

## Flujo B — Registro manual desde la API

1. El usuario llama a `POST /api/devices/self-register` con nombre y,
   opcionalmente, `device_id`, `location` y `mac_address`.
2. El backend genera la `api_key`, vincula el dispositivo y la devuelve **una
   sola vez**.
3. El usuario graba `device_id` + `api_key` en `config.py` del ESP32.

Si la clave se pierde, se puede rotar con
`POST /api/devices/{id}/rotate-key`.

## Endpoints

| Método | Ruta | Autenticación | Descripción |
|---|---|---|---|
| `POST` | `/api/users` | Administrador | Alta de cuenta con correo institucional y contraseña asignada. |
| `PATCH` | `/api/users/{id}` | Administrador | Cambia nombre, rol, estado y restablece contraseña. |
| `GET` | `/api/devices` | Sesión | Dispositivos visibles para el rol. |
| `GET` | `/api/devices/capacity` | Sesión | Cupos totales y del usuario. |
| `POST` | `/api/devices/self-register` | Sesión | Alta manual; devuelve credenciales. |
| `POST` | `/api/devices/provision` | `X-Provisioning-Key` | Alta desde el ESP32 y código temporal. |
| `POST` | `/api/devices/pair` | Sesión | Canjea el código de 6 dígitos. |
| `POST` | `/api/devices` | Administrador | Alta administrativa con `api_key` explícita. |
| `PATCH` | `/api/devices/{id}` | Administrador o propietario | Nombre y ubicación; el admin edita todo. |
| `POST` | `/api/devices/{id}/rotate-key` | Administrador o propietario | Rota la `api_key`. |
| `POST` | `/api/devices/{id}/unpair` | Administrador o propietario | Desvincula sin borrar historial. |
| `DELETE` | `/api/devices/{id}` | Administrador | Elimina dispositivo y mediciones. |
| `GET` | `/api/devices/{id}/measurements?limit=` | Con acceso | Historial del propietario actual. |
| `GET` | `/api/devices/{id}/latest-measurement` | Con acceso | Última medición. |
| `POST` | `/api/devices/ingest` | `X-Device-Api-Key` | Recibe una medición. |
| `POST` | `/api/devices/heartbeat` | `X-Device-Api-Key` | Contacto sin id en la URL. |
| `POST` | `/api/devices/{id}/heartbeat` | `X-Device-Api-Key` | Variante anterior. |

## Firmware y cableado

Archivos del ESP32:

| Archivo | Función |
|---|---|
| `main.py` | WiFi, aprovisionamiento, lectura, envío y heartbeat. |
| `max30102.py` | PPG de luz roja/infrarroja, SpO₂ y pulso. |
| `ds18b20.py` | Temperatura corporal opcional. |
| `pantalla.py` | Display monocromo 128×64 opcional (ESP32 de pruebas de Antonio). |
| `config.example.py` | Plantilla de configuración. Copiar como `config.py`. |

Cableado de referencia:

| Módulo | Pin del módulo | ESP32 |
|---|---|---|
| MAX30102 | VIN / 3V3 | 3V3 |
| MAX30102 | GND | GND |
| MAX30102 | SDA | GPIO 21 |
| MAX30102 | SCL | GPIO 22 |
| DS18B20 | VDD | 3V3 |
| DS18B20 | GND | GND |
| DS18B20 | DQ | GPIO 4, con pull-up de 4.7 kΩ a 3V3 |
| Pantalla monocromo | VCC | 3V3 |
| Pantalla monocromo | GND | GND |
| Pantalla monocromo | SCL | GPIO 22 (comparte bus I2C con el MAX30102) |
| Pantalla monocromo | SDA | GPIO 21 (comparte bus I2C con el MAX30102) |

Verifica la serigrafía de tu módulo: algunos MAX30102 aceptan 3.3 V y otros
requieren nivel lógico de 1.8 V con adaptación. No conectes el sensor al ESP32
mientras esté apagado. La pantalla comparte el bus I2C con el sensor, así que
dos señales más de 21/22 bastan para ambos módulos.

Configuración mínima (`config.py`):

```python
WIFI_SSID = "TU_RED_WIFI"
WIFI_PASSWORD = "TU_CONTRASENA_WIFI"
SERVER_URL = "http://192.168.1.100:8100"
PROVISIONING_KEY = "la-misma-clave-que-.env"

MANUAL_DEVICE_ID = ""
MANUAL_API_KEY = ""
USE_DS18B20 = True
SIMULATION_MODE = False
INTERVAL_MS = 5_000
HEARTBEAT_EVERY_MS = 60_000
```

`config.py` y `device_config.json` contienen secretos, están ignorados por Git
y no se incluyen en el ZIP.

### Comportamiento del firmware

1. Conecta al WiFi y se reconecta si se cae.
2. Si `SIMULATION_MODE=False`, inicializa el MAX30102 y, si está configurado, el
   DS18B20.
3. Cada 5 s intenta una ventana PPG de 4 s. Si la señal no es válida, **no
   envía nada**.
4. Si hay DS18B20, envía `source="esp32"` con temperatura corporal. Si no,
   envía `source="sensor_die"` con la temperatura interna del MAX30102.
5. Envía un heartbeat cada 60 s.
6. Si `SIMULATION_MODE=True`, envía datos aleatorios con
   `source="simulator"` y lo anuncia por el monitor serial.

La fórmula SpO₂ (`110 - 25 × R`) es una aproximación de banco. No es un
dispositivo médico y requiere calibración contra un oximétro de referencia.

## Despliegue real con cuatro usuarias

Plan de la sesión con hardware físico. Un dispositivo por cuenta y las cuentas
las crea el administrador en el panel (**Usuarios → Crear cuenta**), nunca las
usuarias por sí solas.

| Usuaria | Correo institucional | ESP32 |
|---|---|---|
| Areli Orozco | `areli.orozco2936@alumnos.udg.mx` | MAX30102 |
| Leonela Gutierrez | `leonela.gutierrez5405@alumnos.udg.mx` | MAX30102 |
| Anel Sahagún | `anel.sahagun7907@alumnos.udg.mx` | MAX30102 |
| Antonio Montes (comodín, también admin) | `jose.montes6552@alumnos.udg.mx` | MAX30102 **+ pantalla** |

Pasos, en orden:

1. **Alta de cuentas.** El administrador crea las 4 cuentas con su correo
   institucional, rol `paciente` (Antonio, además, `administrador`) y una
   **contraseña primaria** generada con el botón «Generar». La entregan en
   persona y se anota aparte; el sistema no la vuelve a mostrar.
2. **Primer ingreso.** Cada usuaria entra con esa contraseña primaria y la
   cambia en **Tu cuenta → Cambiar tu contraseña** (`POST
   /api/auth/change-password`). A partir de ahí solo ella la conoce y la
   primaria deja de funcionar en ese instante.
3. **Flash de los ESP32.** Con Thonny, a cada placa se le suben `main.py`,
   `max30102.py`, `ds18b20.py` y, si aplica, `pantalla.py` + un `config.py`
   con el mismo WiFi, `SERVER_URL` y `PROVISIONING_KEY`. En el ESP32 de
   Antonio, además, `USE_PANTALLA = True`.
4. **Emparejamiento.** Placa por placa: se enciende el ESP32, pide
   credenciales a `/api/devices/provision` y muestra su **código de 6
   dígitos** (en el monitor serial de Thonny, o en la pantalla si es el de
   Antonio). La usuaria correspondiente inicia sesión y lo ingresa en
   **Mis sensores → Conectar mi sensor**. Con eso la placa queda vinculada a
   su cuenta y empieza a enviar cada 5 s.
5. **Verificación.** El panel de cada usuaria debe mostrar su sensor
   «Recibiendo datos» y solo sus lecturas. Un sensor nunca aparece en la
   cuenta de otra persona.

Si una placa se manda con otra persona o cambia de dueño, el administrador la
desvincula desde la consola de administración y se repite el paso 4.

## Cambio de contraseña por la usuaria

| Ruta | Autenticación | Descripción |
|---|---|---|
| `POST` | `/api/auth/change-password` | La usuaria entrega su contraseña actual (primaria) y la nueva; audita `PASSWORD_CHANGED`. |

Reglas: la nueva necesita mínimo 8 caracteres con letras y números, no puede
repetir la actual, y la incorrecta da `401` sin revelar qué campo falló.

## Desarrollo sin hardware: simulador


Con el servidor en marcha:

```bash
python simulator/prepare_demo.py
python simulator/device_simulator.py
```

`prepare_demo.py` inicia sesión como administrador demo, rota la clave de
`ESP32-O2T-01` y `ESP32-O2T-02`, y escribe `data/demo_credentials.json`. No
imprime las claves en pantalla.

`device_simulator.py` lanza un hilo por dispositivo. Cada uno envía cada 5 s con
`source="simulator"` a su propia `api_key`. Los dos sensores pertenecen a
pacientes distintos, de modo que la demostración comprueba el aislamiento:

| Dispositivo | Propietario demo | Perfil |
|---|---|---|
| `ESP32-O2T-01` | Paciente Demo | SpO₂ 96–98 %, pulso 68–78 lpm. |
| `ESP32-O2T-02` | Paciente Demo Dos | SpO₂ 93–95 %, pulso 82–92 lpm, temperatura 37.3–37.8 °C. |

## Demo simultánea con dos sesiones

1. Servidor: `cd backend; python -m uvicorn app.main:app --host 0.0.0.0 --port 8100`.
2. Terminal 1: `python simulator/prepare_demo.py`.
3. Terminal 2: `python simulator/device_simulator.py`.
4. Navegador A: inicia sesión como `paciente.biomonitor.demo@gmail.com`.
5. Navegador B (incógnito o perfil distinto): inicia sesión como
   `paciente2.biomonitor.demo@gmail.com`.
6. Comprueba que cada perfil ve solo su sensor, su última recepción y su
   historial. Las lecturas deben aparecer en ambos paneles, pero separadas.
7. Detén el simulador o desconecta un ESP32. Tras 90 s sin contacto, el sensor
   pasa a **Desconectado** y el panel conserva los últimos valores.
8. Vuelve a iniciar el simulador. El estado cambia a **Recibiendo datos** en la
   siguiente lectura y el refresco automático (10 s) actualiza el panel.

## Seguridad

- La `api_key` nunca se devuelve en `GET /api/devices`; solo en el alta o al
  rotarla. Se guarda como HMAC-SHA256 con `SECRET_KEY` como pepper.
- El código de emparejamiento se guarda como HMAC, vence, es de un solo uso y
  tiene límite de intentos por usuario.
- `POST /api/devices/provision` exige una clave compartida. Cámbiala en `.env`
  antes de usar el servidor fuera de la red local.
- El propietario solo puede editar nombre y ubicación; no puede cambiar
  `user_id`, `is_active`, `api_key` ni la MAC.
- El propietario de la medición se toma de `devices.user_id`, no del cuerpo.
  Un dispositivo sin vincular recibe `409`; una cuenta inactiva recibe `403`.
- El historial se filtra por el propietario actual del dispositivo. Si se
  reasigna, el nuevo dueño no ve lecturas de la cuenta anterior.
- Desvincular desactiva el dispositivo, rota la `api_key` y conserva las
  mediciones. El cupo global se libera solo al eliminar el dispositivo.
- Se auditan credenciales inválidas, ingestas rechazadas, emparejamientos,
  rotaciones y desvinculaciones, sin registrar claves ni valores del payload.

## Migración y datos demo

`app/database/migrate.py` agrega columnas y convierte claves de dispositivo en
texto plano a HMAC si encuentra una base antigua. Se ejecuta automáticamente al
iniciar el servidor. La semilla crea usuarios, sensores, vínculos y mediciones
`source="demo"` solo si faltan.

Para un servidor real:

```env
SEED_DEMO_DATA=false
```

## Pruebas

```bash
python -m pytest -q
```

La suite cubre alta manual, límites, aprovisionamiento, códigos inválidos y
vencidos, emparejamiento, rotación, desvinculación, permisos, aislamiento entre
usuarios, ingesta no vinculada, historial por propietario, auditoría, alta de
usuarios administrativos y cambio de contraseña por la propia usuaria.
Resultado actual: **77 pruebas aprobadas**.

La validación con hardware físico queda pendiente hasta probar los módulos y el
cableado definitivo.

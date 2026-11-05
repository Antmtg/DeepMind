# BioMonitor O₂T — versión final

Aplicación cliente-servidor para monitoreo académico de signos vitales con
ESP32, FastAPI, SQLite y un panel accesible para cinco roles. El servidor aplica
autenticación, RBAC, separación de datos por propietario y auditoría; el
frontend muestra el origen de cada lectura, el estado de conexión de cada
sensor, el historial y una gráfica con banda de referencia.

> **Alcance:** herramienta académica de apoyo. No diagnostica ni sustituye una
> valoración profesional. La adquisición real con MAX30102/DS18B20 está
> implementada en el firmware, pero la validación física queda pendiente hasta
> contar con los módulos y el cableado definitivo.

## Estado del proyecto

| Área | Estado | Evidencia |
|---|---|---|
| Login, logout y sesión | Implementado | Cookie JWT HttpOnly, pruebas de autenticación. |
| RBAC en el servidor | Implementado | Permisos por rol y pruebas de acceso denegado. |
| Aislamiento entre usuarios | Implementado | Consultas por `user_id`/propietario y pruebas de integración. |
| Dos usuarios y dos ESP32 a la vez | Implementado y probado con simulador | `simulator/device_simulator.py` envía a dos dispositivos de dos dueños. |
| Identificación del origen | Implementado | `esp32`, `sensor_die`, `simulator`, `demo` visibles en tabla y tarjetas. |
| Credenciales de dispositivo | Implementado | HMAC-SHA256; nunca se guardan en texto plano. |
| Historial y gráficas | Implementado | SVG con eje temporal, unidad, banda de referencia y resumen accesible. |
| Estado de conexión | Implementado | Recibiendo, sin lectura nueva, desconectado, desactivado, sin lecturas. |
| Auditoría | Implementado | Accesos, rechazos, emparejamientos, rotaciones y ingestas rechazadas. |
| Adquisición real MAX30102 | Implementado, sin validar en hardware | `device/esp32/max30102.py`. |
| Temperatura corporal DS18B20 | Implementado, opcional | `device/esp32/ds18b20.py`. |
| Validación con hardware físico | Pendiente | Requiere módulos, cableado y oximétro de referencia. |
| Video de respaldo | Pendiente | Debe grabarse con el guion de la sección de demo. |

## Estructura

```text
Biomonitor 2/
├── backend/
│   ├── app/
│   │   ├── api/            # rutas y dependencias de autenticación
│   │   ├── core/           # configuración, seguridad y claves HMAC
│   │   ├── database/       # sesión, migración y semilla demo
│   │   ├── models/         # usuarios, dispositivos, mediciones, vínculos
│   │   ├── schemas/        # contratos Pydantic
│   │   └── services/       # reglas de negocio y consultas
│   ├── requirements.txt
│   └── biomonitor.db       # se crea al iniciar; no se entrega
├── device/esp32/
│   ├── main.py             # WiFi, aprovisionamiento, envío y heartbeat
│   ├── max30102.py         # PPG: SpO2 y pulso
│   ├── ds18b20.py          # temperatura corporal opcional
│   └── config.example.py   # plantilla; copiar como config.py
├── frontend/
│   ├── index.html
│   └── assets/{app.js,styles.css}
├── simulator/
│   ├── prepare_demo.py     # rota claves demo y genera credenciales locales
│   └── device_simulator.py # dos dispositivos simultáneos, source=simulator
├── tests/                  # suite de pytest
├── data/                   # credenciales locales ignoradas por Git
└── docs/
```

## Instalación y ejecución

Requisitos: Python 3.11 o superior. No se necesita Node.js para ejecutar la app.

```bash
python -m pip install -r backend/requirements.txt
```

Crea `.env` a partir de `.env.example` y cambia **al menos** estos valores:

```env
SECRET_KEY=una-clave-larga-aleatoria-y-estable
DEVICE_PROVISIONING_KEY=otra-clave-larga-aleatoria
SEED_DEMO_DATA=true
```

`SECRET_KEY` es también la clave HMAC de las credenciales de dispositivo. Si se
cambia, las claves de los ESP32 ya registrados dejan de validar y hay que
rotarlas.

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8100
```

- Panel: <http://127.0.0.1:8100>
- Salud: <http://127.0.0.1:8100/api/health>
- Swagger: <http://127.0.0.1:8100/docs>
- Desde otro equipo o ESP32: `http://IP_DEL_SERVIDOR:8100`

Para la red local, permite el puerto `8100` en el firewall y reserva una IP fija
para el computador servidor. El ESP32 no puede usar `127.0.0.1`: esa dirección
apunta al propio ESP32.

## Cuentas demo

Contraseña común: `Practica4!`

| Rol | Correo |
|---|---|
| Paciente | `paciente.biomonitor.demo@gmail.com` |
| Paciente 2 | `paciente2.biomonitor.demo@gmail.com` |
| Paciente 3 | `paciente3.biomonitor.demo@gmail.com` |
| Cuidador | `cuidador.biomonitor.demo@gmail.com` |
| Especialista | `especialista.biomonitor.demo@gmail.com` |
| Administrador | `admin.biomonitor.demo@gmail.com` |
| Auditor | `auditor.biomonitor.demo@gmail.com` |

En un servidor real, usa `SEED_DEMO_DATA=false` para no crear cuentas con
contraseña conocida. Las cuentas demo existen solo para la presentación.

## Demo simultánea: dos usuarios y dos dispositivos

### Opción A — Dos ESP32 reales

1. Configura el servidor con `--host 0.0.0.0` y verifica que el ESP32 alcance
   `http://IP_DEL_SERVIDOR:8100/api/health`.
2. Copia `device/esp32/config.example.py` como `config.py` en cada ESP32 y
   completa WiFi, `SERVER_URL` y `PROVISIONING_KEY`.
3. Sube a cada ESP32: `main.py`, `max30102.py`, `ds18b20.py` y `config.py`.
4. Enciende el primer ESP32, copia el código de 6 dígitos del monitor serial e
   ingrésalo en **Mis sensores → Conectar mi sensor** con el usuario 1.
5. Repite con el segundo ESP32 y el usuario 2. Cada equipo queda vinculado a
   una cuenta distinta.
6. Abre dos perfiles de navegador (o una ventana normal y una incógnita) para
   mantener dos sesiones. Inicia sesión como paciente 1 y paciente 2.
7. Comprueba que cada perfil ve su propio sensor y que las lecturas nuevas
   aparecen cada 5 s en el servidor y hasta 10 s después en el panel.

La asociación se guarda en `devices.user_id`; el cuerpo del mensaje nunca puede
elegir al propietario. Un dispositivo sin vincular recibe `409` y no escribe
historial.

### Opción B — Simulador (sin hardware)

En una terminal, con el servidor en marcha:

```bash
# Rota las claves de los dos sensores demo y escribe data/demo_credentials.json
python simulator/prepare_demo.py

# Envía a ambos dispositivos a la vez, cada 5 s, con source="simulator"
python simulator/device_simulator.py
```

El archivo `data/demo_credentials.json` contiene secretos, está ignorado por
Git y **no debe incluirse en el ZIP**. El simulador etiqueta cada lectura como
`simulator`; la interfaz muestra **Simulador (datos simulados)** y no la
presenta como dato real.

Para una prueba rápida:

```bash
python simulator/device_simulator.py --once --seed 7
```

## Adquisición, envío y refresco

| Etapa | Valor | Dónde se configura |
|---|---|---|
| Ventana de muestreo PPG | 4 s a 100 Hz | `MEASUREMENT_WINDOW_S`, `FIFO_SAMPLE_HZ` |
| Intervalo de envío | 5 s | `INTERVAL_MS` |
| Heartbeat | 60 s | `HEARTBEAT_EVERY_MS` |
| Refresco automático del panel | 10 s | `AUTO_REFRESH_MS` en `app.js` |
| Ventana para considerar dato “en vivo” | 15 s | `LIVE_DATA_WINDOW` |
| Ventana para considerar el enlace activo | 90 s | `DEVICE_LINK_WINDOW` |
| Latencia observada en el panel | 0–10 s tras la ingesta | Refresco automático + red |

El firmware no envía una lectura si la señal es insuficiente, si no hay
temperatura válida o si el MAX30102 no responde. Preferimos no mostrar nada
antes que inventar un valor. La temperatura del dado del MAX30102 se envía como
`sensor_die` y la interfaz la marca como referencia del sensor, nunca como
temperatura corporal.

## Seguridad y auditoría

- Contraseñas con **Argon2id** mediante `pwdlib`; nunca se registran en auditoría.
- Sesión con **JWT en cookie HttpOnly**, expiración configurable y cierre de
  sesión del lado del cliente y del servidor.
- **RBAC en el servidor** para paciente, cuidador, especialista, administrador y
  auditor. El frontend oculta acciones, pero la decisión final siempre es del
  backend.
- **Credenciales de dispositivo con HMAC-SHA256** usando `SECRET_KEY` como
  pepper. La `api_key` en claro solo se devuelve al registrarla o rotarla.
- **Propietario desde la base de datos**, no desde el payload. La ingesta exige
  dispositivo vinculado y cuenta activa.
- **Historial filtrado por el propietario actual** del dispositivo; si un equipo
  se reasigna, el nuevo dueño no ve lecturas de la cuenta anterior.
- **Código de emparejamiento** de 6 dígitos, guardado como HMAC, con TTL de 10
  minutos, un solo uso y límite de intentos.
- **Auditoría** de login/logout, accesos denegados, aprovisionamiento, registro,
  emparejamiento, fallos de emparejamiento, rotación, desvinculación,
  credenciales de dispositivo rechazadas e ingestas rechazadas. No se auditan
  contraseñas, tokens ni el contenido de los payloads.
- `SECRET_KEY` y `DEVICE_PROVISIONING_KEY` viven en `.env`; `config.py` y
  `device_config.json` viven solo en el ESP32 y están ignorados por Git.

## Panel, historial y gráficas

- El paciente ve sus sensores, la última recepción, la última lectura, el origen
  del dato y su estado de conexión.
- El historial permite elegir 10, 30, 60 o 100 lecturas. La gráfica y la tabla
  usan el mismo rango.
- Hay tres gráficas SVG: SpO₂, pulso y temperatura corporal. Incluyen eje
  temporal, unidad, banda de referencia, resumen de mínimo/máximo/último valor y
  una descripción accesible para lectores de pantalla.
- Las lecturas de temperatura `sensor_die` se excluyen de la gráfica corporal y
  se identifican en la tabla.
- Cuidador y especialista ven el detalle de sus pacientes asignados con el mismo
  historial y las mismas gráficas.
- El administrador ve el estado de contacto de cada sensor y puede editarlo,
  activarlo o desactivarlo.
- El auditor filtra por resultado/acción y exporta CSV.

### Estados de conexión

| Estado | Significado |
|---|---|
| **Recibiendo datos** | Hay una lectura dentro de los últimos 15 s. |
| **En línea, sin lectura nueva** | Hubo contacto en los últimos 90 s, pero la última lectura es anterior. |
| **Desconectado** | El último contacto tiene más de 90 s. Se muestran los últimos valores recibidos. |
| **Desactivado** | El administrador desactivó el sensor; se conserva el historial. |
| **Sin lecturas** | Nunca se recibió una medición. |

## API principal

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `POST` | `/api/auth/login` | Público | Inicia sesión y crea la cookie JWT. |
| `POST` | `/api/auth/logout` | Sesión | Cierra la sesión. |
| `GET` | `/api/dashboard` | Sesión | Datos base del rol. |
| `GET` | `/api/care/patients` | Cuidador, especialista | Pacientes con vínculo activo. |
| `GET` | `/api/care/patients/{id}?limit=` | Cuidador, especialista | Detalle, sensores e historial. |
| `GET` | `/api/devices` | Sesión | Dispositivos visibles según rol y vínculos. |
| `GET` | `/api/devices/{id}/measurements?limit=` | Con acceso | Historial del propietario actual. |
| `GET` | `/api/devices/{id}/latest-measurement` | Con acceso | Última medición. |
| `POST` | `/api/devices/provision` | `X-Provisioning-Key` | Alta y código de emparejamiento. |
| `POST` | `/api/devices/pair` | Sesión | Canjea el código de 6 dígitos. |
| `POST` | `/api/devices/ingest` | `X-Device-Api-Key` | Ingesta autenticada por dispositivo. |
| `POST` | `/api/devices/heartbeat` | `X-Device-Api-Key` | Último contacto. |
| `POST` | `/api/devices/{id}/rotate-key` | Propietario o admin | Rota la `api_key`. |
| `POST` | `/api/devices/{id}/unpair` | Propietario o admin | Desvincula y conserva historial. |
| `GET` | `/api/audit` | Auditor | Eventos filtrados por estado/acción. |

## Pruebas

```bash
python -m pytest -q
node --check frontend/assets/app.js
```

Resultado actual: **62 pruebas aprobadas**. La suite cubre autenticación, RBAC,
vínculos de cuidado, dispositivos, emparejamiento, rotación de claves,
aislamiento entre usuarios, ingesta no vinculada, historial por propietario y
auditoría. La validación con hardware físico sigue pendiente.

## Resultados esperados y obtenidos

| Requisito | Esperado | Obtenido | Corrección aplicada |
|---|---|---|---|
| Login/logout | Sesión segura y cierre real | Implementado y probado | Cookie HttpOnly y logout del servidor. |
| RBAC | Cada rol solo accede a lo suyo | Implementado y probado | Dependencias `require_roles` en todas las rutas sensibles. |
| Dos usuarios y dos ESP32 | Datos separados en tiempo real | Simulador simultáneo verificado; hardware pendiente | Propietario desde `devices.user_id`, no desde el payload. |
| Origen de cada dato | Etiqueta visible y fiable | Implementado | `source` obligatorio y etiquetas en UI/tabla. |
| Credenciales de dispositivo | No guardar secretos en claro | Implementado | HMAC-SHA256 con `SECRET_KEY`. |
| Ingesta sin vincular | No debe crear historial | Implementado y probado | `409` + auditoría `DEVICE_DATA_REJECTED`. |
| Historial tras reasignación | No filtrar datos del dueño anterior | Implementado y probado | Filtro por propietario actual. |
| Historial y gráfica | Tendencias con tiempo y unidades | Implementado | SVG con banda de referencia y resumen accesible. |
| Desconexión | Distinguir en vivo, sin lectura y desconectado | Implementado | `last_seen` + última lectura con ventanas de 15/90 s. |
| Datos demo | No confundirlos con ESP32 | Implementado | Semilla con `source="demo"`; claves aleatorias hasheadas. |
| Firmware | Lectura real; simulación opt-in | Implementado, sin validar | MAX30102/DS18B20; `SIMULATION_MODE=False` por defecto. |
| Documentación | Frecuencias, red y demo | Implementado | Este README y `docs/conexion-dispositivos.md`. |
| PDF, PPTX y video | Entregables finales | PDF/PPTX generados con placeholders; video pendiente | Completar nombres, capturas y grabar respaldo. |

## Matriz de cumplimiento

| Requisito de la práctica | Estado | Dónde se demuestra |
|---|---|---|
| Login, logout y sesión | Cumplido | `/api/auth/*`, panel, pruebas. |
| RBAC aplicado en servidor | Cumplido | `require_roles`, pruebas de 403. |
| Sin lecturas cruzadas entre usuarios | Cumplido | Filtros por propietario, `test_final_integration.py`. |
| Dos usuarios y dos ESP32 simultáneos | Cumplido con simulador; hardware pendiente | `simulator/device_simulator.py`. |
| Identificar el origen de cada registro | Cumplido | `source` y etiquetas en la UI. |
| Credencial por dispositivo y asociación validada | Cumplido | HMAC, `provision`, `pair`, `ingest`. |
| Última lectura, fecha/hora y última recepción | Cumplido | Tarjetas de sensor y tablas. |
| Estado de actualización y desconexión | Cumplido | `deviceStatusInfo`, ventanas de 15/90 s. |
| Historial y gráfica adecuada | Cumplido | SVG SpO₂/pulso/temperatura. |
| Frecuencias y retardo documentados | Cumplido | Sección de adquisición. |
| Contraseñas hasheadas | Cumplido | Argon2id. |
| Secretos fuera del código entregado | Cumplido | `.env`, `config.py`, `.gitignore`. |
| Auditoría de accesos, rechazos y asociaciones | Cumplido | `audit_logs`, acciones `DEVICE_*`. |
| Resultados esperados vs obtenidos | Cumplido | Tabla anterior. |
| README de instalación y demo | Cumplido | Este documento. |
| PDF, PPTX y ZIP sin artefactos | Parcial | PDF/PPTX generados; ZIP y video pendientes de cierre. |

## Limitaciones y pendientes

1. **Validación física:** no se han probado MAX30102 ni DS18B20 con el hardware
   definitivo. La fórmula SpO₂ es una aproximación de banco y requiere
   calibración contra un oximétro de referencia.
2. **Video de respaldo:** debe grabarse mostrando dos sesiones, dos dispositivos,
   desconexión/reconexión, historial y gráficas.
3. **Datos personales:** completar nombres, grupo, institución y capturas reales
   en el informe y la presentación.
4. **Producción:** para exponer el servidor fuera de la red local se requiere
   HTTPS, proxy inverso, `SEED_DEMO_DATA=false` y secretos nuevos.

## Entregables y ZIP

El ZIP final debe incluir código, pruebas, documentación y las plantillas de
configuración. **No incluir**:

- `.venv/`, `venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`
- `.env`, `backend/biomonitor.db`, `*.db`, `*.sqlite3`
- `data/demo_credentials.json`
- `device/esp32/config.py`
- `device/esp32/device_config.json`
- contraseñas reales, tokens o archivos ajenos a la práctica

Checklist rápido:

```text
[ ] PDF del informe final
[ ] Presentación PPTX/PDF
[ ] ZIP sin entornos virtuales, cachés, bases ni secretos
[ ] Video de respaldo
[ ] Dos sesiones + dos dispositivos probados
[ ] Gráficas e historial visibles
[ ] Desconexión/reconexión demostrada
[ ] README y matriz de cumplimiento revisados
```

## Documentación

- [`docs/conexion-dispositivos.md`](docs/conexion-dispositivos.md): flujos de
  conexión, endpoints, seguridad, firmware y demo simultánea.
- [`docs/informe-final.md`](docs/informe-final.md): informe académico con
  objetivos, diseño, resultados y conclusiones.
- [`docs/presentacion-final.md`](docs/presentacion-final.md): guion de
  diapositivas y demostración.
- [`docs/estado-sesion.md`](docs/estado-sesion.md): estado de cierre y
  pendientes.
- [`CHANGELOG.md`](CHANGELOG.md): cambios de la versión final.

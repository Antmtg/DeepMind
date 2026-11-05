# Estado de la sesión — versión final

Fecha de cierre: 4 de noviembre de 2026.

## Resumen

La versión final cierra la práctica con los requisitos funcionales y de seguridad
centrales implementados: autenticación, RBAC en el servidor, separación de datos
por propietario, dos dispositivos simultáneos, origen visible de cada lectura,
historial con gráficas, estados de conexión, auditoría y documentación.

Además, el firmware del ESP32 dejó de generar valores aleatorios por defecto.
Ahora lee un MAX30102 real, usa un DS18B20 opcional para temperatura corporal y
solo simula si `SIMULATION_MODE=True`, marcando cada lectura como `simulator`.

## Estado actual

- Backend y frontend corriendo en `http://127.0.0.1:8100/`.
- Suite automática: **62 pruebas aprobadas**.
- Frontend verificado en navegador con sesiones de paciente, cuidador,
  administrador y auditor.
- Simulador de dos dispositivos probado con `ESP32-O2T-01` y `ESP32-O2T-02`,
  cada uno con su propia clave y su propio propietario.
- Base demo con tres sensores, uno por paciente, y mediciones `source="demo"`.
- Credenciales locales de demostración en `data/demo_credentials.json`
  (ignorado por Git; no se entrega).
- Repositorio Git con cambios sin confirmar al cierre de esta sesión.

## Cómo iniciar el proyecto

```bash
python -m pip install -r backend/requirements.txt
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8100
```

Abrir `http://127.0.0.1:8100/`.

Pruebas y verificación de sintaxis:

```bash
python -m pytest -q
node --check frontend/assets/app.js
python -m py_compile device/esp32/main.py device/esp32/max30102.py device/esp32/ds18b20.py device/esp32/config.example.py
```

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

## Datos demo

- `Sensor A · sala` (`ESP32-O2T-01`): lectura normal, paciente demo 1.
- `Sensor B · dormitorio` (`ESP32-O2T-02`): lectura para revisar, paciente demo 2.
- `Sensor C · reserva` (`ESP32-O2T-03`): sin lecturas, paciente demo 3.
- Un sensor por paciente demo, según la regla de auto-vinculo.
- Vínculo activo del paciente principal con el cuidador y el especialista demo.

Las lecturas de la semilla se identifican como **Datos de ejemplo**. Las del
simulador se identifican como **Simulador (datos simulados)** y las del ESP32
real como **ESP32 (sensor real)** o **ESP32 · temp. interna**.

## Implementado en el cierre final

### Seguridad y backend

- Credenciales de dispositivo guardadas como **HMAC-SHA256** con `SECRET_KEY`
  como pepper; migración automática de claves antiguas en texto plano.
- Ingesta rechazada con `409` si el dispositivo no está vinculado y con `403` si
  la cuenta propietaria está inactiva; ambos casos se auditan.
- Historial filtrado por el propietario actual del dispositivo para evitar fugas
  tras una reasignación.
- Semilla demo con `source="demo"` y claves aleatorias hasheadas, sin secretos
  en el código.
- Endpoint de detalle de paciente con `limit` y mediciones con `device_id` y
  `source` para las gráficas del cuidador.
- Pruebas de integración final: **62 aprobadas**.

### Frontend

- Gráficas SVG de SpO₂, pulso y temperatura con eje temporal, unidad, banda de
  referencia, resumen accesible y estado vacío.
- Selector de historial de 10, 30, 60 o 100 lecturas, compartido por la gráfica
  y la tabla, en paciente y en detalle de cuidador/especialista.
- Estado por sensor: recibiendo datos, en línea sin lectura nueva, desconectado,
  desactivado y sin lecturas.
- Tarjetas de sensor con última recepción, última lectura, origen y valores.
- Resúmenes de origen dinámicos en lugar de textos fijos “Datos de ejemplo”.
- Refresco automático activo cada 10 s; ventana de dato en vivo de 15 s y de
  enlace activo de 90 s.
- Etiquetas y filtros de auditoría para eventos de dispositivo.

### Firmware y simulador

- `device/esp32/max30102.py`: configuración I2C, FIFO, estimación AC/DC de SpO₂,
  detección de picos para pulso y temperatura interna; devuelve `None` si la
  señal no es válida.
- `device/esp32/ds18b20.py`: temperatura corporal opcional por OneWire.
- `device/esp32/main.py`: WiFi, aprovisionamiento, lectura real, heartbeat,
  reconexión y simulación solo si se activa explícitamente.
- `device/esp32/config.example.py`: plantilla sin secretos.
- `simulator/prepare_demo.py`: rota las claves de dos sensores demo y escribe
  `data/demo_credentials.json`.
- `simulator/device_simulator.py`: dos hilos, dos propietarios, cada 5 s, con
  `source="simulator"`.

### Documentación y entregables

- `README.md` con instalación, red, firmware, demo simultánea, intervalos,
  latencia, seguridad, API, pruebas y matriz de cumplimiento.
- `docs/conexion-dispositivos.md` con flujos, endpoints, cableado y simulador.
- `docs/informe-final.md` y `docs/presentacion-final.md` como fuentes del PDF y
  del PPTX.
- PDF del informe y PPTX de la presentación generados en `docs/`.
- Capturas de la aplicación en `docs/capturas/`.

## Validación realizada

- `python -m pytest -q`: **62 pruebas aprobadas**.
- `node --check frontend/assets/app.js`: correcto.
- `python -m py_compile` del firmware: correcto.
- Login y restauración de sesión.
- Panel de paciente con gráficas, historial y estados.
- Panel de cuidador y detalle de paciente con gráficas.
- Panel de administrador con estado de cada sensor.
- Panel de auditoría con filtros y eventos de dispositivo.
- Simulador de dos dispositivos con datos separados por propietario.
- Cambio de rango de historial y refresco automático cada 10 s.

## Pendientes

1. **Validación física:** probar MAX30102 y DS18B20 con los módulos y el cableado
   definitivos; comparar SpO₂ con un oximétro de referencia y ajustar la
   calibración.
2. **Video de respaldo:** grabar la demo con dos sesiones, dos dispositivos,
   desconexión/reconexión, historial y gráficas.
3. **Datos personales:** completar nombres, grupo, institución, docente y fecha
   en el informe y la presentación.
4. **Commit y etiqueta:** confirmar los cambios y etiquetar la versión final.
5. **ZIP:** generar el paquete sin entornos virtuales, cachés, bases de datos ni
   secretos.

## Archivos principales

- `frontend/index.html`: shell del panel, diálogos y textos de estado.
- `frontend/assets/styles.css`: sistema visual, gráficas, historial y responsive.
- `frontend/assets/app.js`: roles, gráficas, historial, estados, auditoría y
  emparejamiento.
- `backend/app/services/device_service.py`: claves HMAC, capacidad, aprovisionamiento,
  emparejamiento, rotación y desvinculación.
- `backend/app/api/routes/devices.py`: ingesta validada y auditoría.
- `backend/app/services/care_service.py`: detalle de paciente con historial.
- `backend/app/database/seed.py`: usuarios, sensores, vínculos y mediciones demo.
- `device/esp32/main.py`: firmware principal.
- `device/esp32/max30102.py`: controlador y algoritmos del sensor óptico.
- `device/esp32/ds18b20.py`: temperatura corporal opcional.
- `device/esp32/config.example.py`: plantilla de configuración.
- `simulator/prepare_demo.py`: preparación de credenciales demo.
- `simulator/device_simulator.py`: simulador de dos dispositivos.
- `tests/test_final_integration.py`: pruebas de cierre.
- `docs/informe-final.md`, `docs/presentacion-final.md`, `README.md`: documentación.

## Documentación

- [`README.md`](../README.md): instalación, demo, seguridad y cumplimiento.
- [`docs/conexion-dispositivos.md`](conexion-dispositivos.md): conexión de hardware.
- [`docs/informe-final.md`](informe-final.md): informe académico.
- [`docs/presentacion-final.md`](presentacion-final.md): guion de diapositivas.
- [`CHANGELOG.md`](../CHANGELOG.md): cambios y decisiones.

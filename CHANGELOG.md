# Cambios de BioMonitor O₂T

Este documento registra los cambios de la versión final y de las versiones anteriores, con las razones (**porqués**) de cada decisión. Se preparó para dejar constancia del trabajo y facilitar la continuación.

---

## Versión 4.1 — Contraseña propia y pantalla (4 de noviembre de 2026)

### Qué se hizo

- **Cambio de contraseña por la usuaria**: `POST /api/auth/change-password`
  pide la contraseña actual (la primaria que entregamos) y la nueva. La
  primaria deja de funcionar en el momento del cambio. Audita
  `PASSWORD_CHANGED` y rechaza contraseñas débiles o repetidas.
- **Panel «Tu cuenta»**: formulario *Cambiar tu contraseña* con verificación
  de repetición y mensajes claros.
- **Pantalla del ESP32** (`device/esp32/pantalla.py`): driver monocromo I2C
  128×64 (SSD1306/SH1106) con texto de pixeles grandes. Muestra SpO₂ grande,
  pulso, temperatura, estado («Leyendo y enviando», «Sin señal del sensor»,
  «Sin enlace con servidor») y el **código de emparejamiento de 6 dígitos** en
  pantalla para Antonio. Si la pantalla falla, el ESP32 sigue midiendo.
- **Plan de despliegue real** documentado en `docs/conexion-dispositivos.md`
  con la tabla de las cuatro cuentas y los pasos de emparejamiento.

### Por qué

La contraseña la entrega el equipo en persona y la usuaria la cambia al
primer ingreso: así nadie más conoce su contraseña definitiva y no hacemos
falta de envío de correos. Y con el código de emparejamiento visible en la
pantalla del ESP32 de Antonio es posible emparejar sin depender del monitor
serial.

---

## Versión 4.0 — Alta de usuarios y despliegue local (4 de noviembre de 2026)

### Qué se hizo

- **Alta de cuentas por el administrador:** `POST /api/users` crea cuentas con
  correo institucional y contraseña asignada por nosotros. No existe
  autoregistro por diseño: la contraseña se entrega en persona.
- **Gestión de cuentas:** `PATCH /api/users/{id}` permite cambiar nombre, rol,
  estado y restablecer la contraseña. Se protege la última cuenta
  administradora activa del sistema.
- **Servicio de usuarios** (`app/services/user_service.py`): política de
  contraseñas (mínimo 8 caracteres, letras y números, sin el nombre de
  usuario) y validación de roles.
- **Auditoría:** las altas, cambios y restablecimientos se registran como
  `USER_CREATED`, `USER_UPDATED` y `USER_PASSWORD_RESET`, sin guardar nunca la
  contraseña.
- **Panel admin:** la sección «Usuarios» tiene formulario de alta con botón
  «Generar» de contraseñas seguras y botón «Editar» por fila (rol, estado y
  contraseña nueva en diálogo). El aviso "no se crean cuentas nuevas" se
  retira.
- **Pruebas:** 10 casos nuevos en `tests/test_users_admin.py`; suite en 72
  pruebas aprobadas.

### Por qué

Para el despliegue real con las cuatro usuarias (Areli, Leonela, Anel y
Antonio como comodín de pruebas) hace falta que el administrador cree las
cuentas y asigne contraseñas; el registro abierto no era aceptable para un
servidor casero con datos de salud.

---

## Versión final — cierre de la práctica (4 de noviembre de 2026)

### Qué se hizo

- **Seguridad de credenciales:** las `api_key` de los dispositivos se guardan
  como **HMAC-SHA256** usando `SECRET_KEY` como pepper. La migración convierte
  automáticamente las claves antiguas en texto plano. La clave en claro solo se
  devuelve al registrar o rotar.
- **Ingesta validada:** un dispositivo sin propietario recibe `409`; una cuenta
  inactiva recibe `403`. Ambos rechazos se auditan como `DEVICE_DATA_REJECTED` y
  `DEVICE_AUTH_FAILED` sin registrar la credencial ni el payload.
- **Aislamiento de historial:** las mediciones se consultan por el propietario
  actual del dispositivo, no por el `user_id` histórico. Si un sensor se
  reasigna, el nuevo dueño no ve lecturas de la cuenta anterior.
- **Semilla demo:** las mediciones usan `source="demo"` y las claves de los
  sensores se generan aleatoriamente y se guardan hasheadas. No hay secretos en
  el código entregado.
- **Detalle de paciente:** `GET /api/care/patients/{id}` acepta `limit` y cada
  medición incluye `device_id` y `source` para construir las gráficas.
- **Gráficas SVG:** SpO₂, pulso y temperatura con eje temporal, unidad, banda de
  referencia, resumen de mínimo/máximo/último, descripción accesible y estado
  vacío. La temperatura `sensor_die` se excluye de la gráfica corporal.
- **Historial configurable:** selector de 10, 30, 60 o 100 lecturas en paciente y
  en el detalle de cuidador/especialista; la gráfica y la tabla usan el mismo
  rango.
- **Estados de conexión:** recibiendo datos (≤ 15 s), en línea sin lectura nueva
  (≤ 90 s), desconectado, desactivado y sin lecturas. Se muestran la última
  recepción, la última lectura y el origen.
- **Textos dinámicos:** se reemplazaron los textos fijos “Datos de ejemplo” por
  resúmenes basados en el `source` real de las lecturas.
- **Refresco automático:** activo por defecto cada 10 s; la etiqueta y la guía
  rápida se corrigieron para reflejar ese intervalo.
- **Auditoría:** etiquetas y filtros para eventos `DEVICE_*`.
- **Firmware real:** `device/esp32/max30102.py` configura el sensor, lee la FIFO
  y estima SpO₂ y pulso; `ds18b20.py` agrega temperatura corporal opcional;
  `main.py` usa WiFi, aprovisionamiento, heartbeat y reconexión. Sin lectura
  válida no se envía nada. La simulación requiere `SIMULATION_MODE=True` y se
  marca como `simulator`.
- **Plantilla de configuración:** `device/esp32/config.example.py` con WiFi,
  servidor, pines, tiempos y calibración, sin secretos.
- **Simulador de dos dispositivos:** `simulator/prepare_demo.py` rota las claves
  de dos sensores demo y `device_simulator.py` envía desde dos hilos a dos
  propietarios distintos cada 5 s con `source="simulator"`.
- **Pruebas:** se agregó `tests/test_final_integration.py`; la suite pasó de 56 a
  **62 pruebas aprobadas**.
- **Documentación:** README reescrito con instalación, red, firmware, demo
  simultánea, intervalos, latencia, seguridad, API, resultados esperados vs
  obtenidos y matriz de cumplimiento. Se actualizaron
  `docs/conexion-dispositivos.md`, `docs/estado-sesion.md`, el informe final y la
  presentación.
- **Entregables:** PDF del informe, PPTX de la presentación y capturas en
  `docs/`.

### Por qué

- Guardar claves en texto plano permitía que una copia de la base expusiera todos
  los dispositivos. El HMAC conserva la verificación sin almacenar el secreto.
- Aceptar ingestas de dispositivos sin dueño rompía el aislamiento: cualquiera
  con una clave podía escribir en un historial sin propietario.
- Consultar el historial por el `user_id` de la medición podía filtrar datos
  después de una reasignación; el propietario actual es la referencia correcta.
- Un firmware que inventa lecturas cuando el sensor falla es peligroso en un
  contexto de salud. Es preferible mostrar el último dato con su fecha y estado.
- La simulación debía ser explícita y visible para no confundir una demostración
  con una medición física.
- El panel necesitaba responder cuatro preguntas: qué se midió, cuándo llegó, de
  qué sensor y si sigue conectado.

---

## 0. Conexión de dispositivos ESP32 por código serial (versión 3.1.1)

### Qué se hizo

- **Frontend — diálogo de emparejamiento (`pair-dialog`)**: se agregó a `frontend/index.html` un diálogo nativo titulado "Vincula tu sensor ESP32" con instrucciones para el monitor serial (115200 baudios, línea `CODIGO DE EMPAREJAMIENTO`), campo de texto de exactamente 6 dígitos (`inputmode="numeric"`, `pattern="[0-9]{6}"`, `autocomplete="one-time-code"`), aviso de vencimiento de 10 minutos y zona de errores de formulario.
- **Frontend — consulta de capacidad**: `openPairDialog()` llama a `GET /api/devices/capacity` antes de habilitar el botón "Vincular sensor". Si no hay cupos globales o la cuenta ya alcanzó su límite (1 sensor por usuario), se muestra un aviso bloqueado y el botón queda deshabilitado.
- **Frontend — envío del código**: `submitPairForm()` valida localmente que el código tenga 6 dígitos y envía `POST /api/devices/pair` con `{ pairing_code }`. Maneja respuestas 400 (código inválido/vencido), 403 (sensor desactivado), 409 (ya vinculado), 422 (formato inválido) y 429 (demasiados intentos) con mensajes en español.
- **Frontend — desvinculación**: cada tarjeta de sensor en el panel de paciente muestra un botón "Desvincular" que llama a `POST /api/devices/{id}/unpair` tras una confirmación explícita. El dispositivo se desactiva, rota su `api_key`, conserva el historial de mediciones y se avisa al usuario.
- **Frontend — estado de dispositivos**: `loadPatientDashboard()` ahora guarda los dispositivos en `dashState.devices` para que las acciones de desvinculación puedan encontrarlos. La sección "Mis sensores" muestra el botón "Conectar mi sensor" cuando la cuenta no tiene sensores.
- **Frontend — CSS**: se agregaron estilos para `sensor-actions`, `pair-steps`, `pair-capacity` (estado normal y bloqueado), `pair-code-field` (código centrado y espaciado) y `pair-code-hint`.
- **Backend — endpoints de dispositivos**: `GET /api/devices/capacity`, `POST /api/devices/pair`, `POST /api/devices/{id}/unpair` (ya implementados en el backend, ahora expuestos desde el panel de paciente).
- **Pruebas**: la suite pasó de 35 a **56 pruebas aprobadas** (`python -m pytest -q`), cubriendo emparejamiento, límites de capacidad, códigos inválidos/vencidos/reutilizados, rotación de clave, desvinculación y conservación del historial.

### Por qué

- El emparejamiento por código serial (sin Bluetooth ni proximidad) permite conectar varios ESP32 en el mismo aula sin ambigüedad: cada dispositivo imprime su propio código de 6 dígitos.
- Los códigos son HMAC-SHA256, de un solo uso, expiran a los 10 minutos y están rate-limitados por usuario, dificultando fuerza bruta sobre 6 dígitos.
- La desvinculación rota inmediatamente la `api_key`, por lo que el ESP32 deja de enviar mediciones y debe borrar `device_config.json` y solicitar un código nuevo si se quiere volver a conectar.
- Un sensor por cuenta y máximo 5 en total protege al servidor casero de sobrecarga en el aula.

---

## 1. Rediseño del panel para los cinco roles (versión 3.1)

### Qué se hizo
Se reemplazó el panel anterior por un shell común con:
- Barra lateral de navegación en escritorio y navegación inferior en móvil.
- Encabezado con saludo, rol, botón de actualizar, ayuda, accesibilidad y cuenta.
- Área principal `#dash-content` que renderiza el contenido según el rol.
- Diálogos nativos para ayuda, cuenta, accesibilidad, detalle de paciente, edición de sensor y confirmaciones.
- Pie con privacidad y términos.

### Por qué
- **Un solo shell** evita duplicar maquetado y facilita el mantenimiento.
- **Navegación inferior en móvil** responde a la investigación sobre usuarios mayores: acciones evidentes y al alcance del pulgar, sin gestos ocultos.
- **Lenguaje en «tú»** y estados claros hacen que el panel sea comprensible para personas con poca familiaridad tecnológica.
- **Aviso permanente de «Datos de ejemplo»** evita confundir la demo con información clínica real.

---

## 2. Vínculos reales de cuidado (`care_assignments`)

### Qué se hizo
- Se agregó la tabla `care_assignments` con los campos `id`, `patient_id`, `member_id`, `relationship`, `is_active` y `created_at`.
- Restricción única sobre `(patient_id, member_id)` para evitar duplicados.
- Endpoints: `GET /api/care/patients`, `GET /api/care/patients/{id}`, `GET/POST/DELETE /api/care/assignments`.
- Seed con dos vínculos activos: paciente–cuidador y paciente–especialista.
- Los tres sensores demo pertenecen al paciente.

### Por qué
- Antes «Mis pacientes» no tenía respaldo real; ahora un cuidador o especialista solo ve a los pacientes con los que tiene un vínculo activo.
- El vínculo se puede desactivar sin borrar el historial, manteniendo trazabilidad.
- El tipo de vínculo debe coincidir con el rol del miembro para evitar asignaciones incorrectas.

---

## 3. Endpoints y reglas de acceso del backend

### Qué se hizo
- `DevicePublic` ya no expone `api_key`; agrega `owner_name`.
- Creación, edición y eliminación de dispositivos exclusiva del administrador.
- Acceso a detalle, historial y última medición respeta propiedad y asignaciones activas.
- `GET /api/devices/{id}/measurements` acepta `limit` de 1 a 200.
- `GET /api/audit` acepta filtros `status`, `action` y `offset`.
- `temperature_source` deriva de `Measurement.source`.
- Timestamps de mediciones en hora local; auditoría/usuarios/asignaciones en UTC, serializados a hora local al leer.

### Por qué
- No exponer `api_key` protege la credencial de los dispositivos ESP32.
- Separar responsabilidades reduce el riesgo de acciones accidentales (solo admin gestiona dispositivos y vínculos).
- Los filtros de auditoría permiten al auditor revisar eventos sin cargar todo el historial.
- UTC en auditoría garantiza trazabilidad consistente independientemente de la zona horaria del servidor.

---

## 4. Frontend: lógica, estados y administración

### Qué se hizo
- `frontend/assets/app.js` reescrito con navegación por rol, carga dinámica, administración de sensores y vínculos, auditoría con filtros y exportación CSV, y preferencias de accesibilidad.
- Estados visuales con texto y color: **En rango**, **Para revisar**, **Necesita atención**, **Sin lectura**, **Sin lectura reciente**.
- Acciones de administración con confirmación: editar sensor, activar/desactivar, crear/desactivar/reactivar vínculo, detectar duplicados.
- Panel técnico RBAC colapsado bajo **Detalles técnicos**.

### Por qué
- Los estados incluyen texto además de color para que no dependan solo del daltonismo o la percepción del color.
- Las confirmaciones explican la consecuencia antes de acciones irreversibles o sensibles.
- El panel técnico se conserva para la evaluación académica sin competir con la información de salud.

---

## 5. Accesibilidad y diseño senior-first

### Qué se hizo
- Texto base de 18 px; preferencias Normal (18 px), Grande (20 px) y Muy grande (23 px).
- Objetivos táctiles mínimos de 48 × 48 px.
- Foco visible de 3 px en botones, enlaces y campos.
- Enlaces de salto al contenido.
- Diálogos nativos cerrables con Escape.
- Etiquetas `aria-label`, `aria-pressed`, `aria-current`, `role="status"` y regiones `aria-live`.
- Alto contraste disponible.
- Respeto a `prefers-reduced-motion` y opción de reducir movimiento.
- Reflow sin desplazamiento horizontal de página al 200 % de zoom (720 px).
- Tablas anchas con desplazamiento interno.

### Por qué
- La investigación (W3C WAI, NN/g, WCAG 2.2) indica que las personas mayores necesitan texto grande, objetivos grandes, contraste alto, foco visible y navegación predecible.
- Lighthouse verificó 100 en Accesibilidad, Buenas prácticas y SEO en los paneles de paciente y administrador.

---

## 6. Documentación

### Qué se hizo
- `docs/reporte-dashboard.md`: investigación de competidores, decisiones de diseño, vínculos, accesibilidad y resultados de validación.
- `docs/estado-sesion.md`: estado de la versión 3.1, datos demo, comandos y pendientes.
- `README.md`: actualizado con nuevos endpoints, cuentas demo, datos de ejemplo, reglas de acceso y accesibilidad.

### Por qué
- Dejar constancia de las decisiones de diseño y la investigación respalda la práctica académica y facilita la continuidad del proyecto.

---

## 7. Pruebas (versión 3.1)

### Qué se hizo
- `tests/test_care.py` expandido con pruebas de asignaciones, permisos, auditoría y serialización de fechas.
- `tests/test_devices.py` actualizado con los nuevos accesos y campos.
- Total de la versión 3.1: **35 pruebas aprobadas** con `python -m pytest -q`.

### Por qué
- Validar que RBAC, asignaciones, dispositivos y auditoría funcionen correctamente antes de entregar la versión.

---

## 8. Pruebas (versión 3.1.1)

### Qué se hizo
- `tests/test_device_pairing.py` agregado con 21 pruebas de emparejamiento, límites de capacidad, códigos inválidos/vencidos/reutilizados, rate limiting, rotación de `api_key`, desvinculación y conservación del historial.
- Total acumulado: **56 pruebas aprobadas** con `python -m pytest -q`.
- `node --check frontend/assets/app.js`: sintaxis correcta.
- Validación en navegador con base temporal: flujo de conectar, reintentar con código inválido y desvincular verificado contra la API real.

### Por qué
- Asegurar que el emparejamiento serial, la capacidad y la desvinculación funcionen correctamente antes de entregar la versión 3.1.1.

---

## Resumen de archivos principales

| Archivo | Contenido |
|---|---|
| `frontend/index.html` | Shell del panel, diálogos, panel técnico y diálogo de emparejamiento `pair-dialog` |
| `frontend/assets/styles.css` | Sistema visual, responsive, accesibilidad y estilos de emparejamiento/desvinculación |
| `frontend/assets/app.js` | Navegación, contenido por rol, administración, preferencias, emparejamiento y desvinculación |
| `backend/app/models/assignment.py` | Modelo `care_assignments` |
| `backend/app/services/care_service.py` | Consultas y reglas de acceso de cuidado |
| `backend/app/api/routes/care.py` | Endpoints de cuidado y asignaciones |
| `backend/app/api/routes/devices.py` | Endpoints de dispositivos: lista, capacidad, pair, unpair, rotate-key, ingest, heartbeat |
| `backend/app/services/device_service.py` | Acceso a dispositivos, emparejamiento, capacidad, rotación y desvinculación |
| `backend/app/database/seed.py` | Usuarios, sensores, vínculos y mediciones demo (un sensor por paciente) |
| `backend/app/core/config.py` | `MAX_DEVICES`, `MAX_DEVICES_PER_USER`, TTL y rate limiting de emparejamiento |
| `backend/app/core/rate_limit.py` | Limitador en memoria de intentos de emparejamiento por usuario |
| `backend/app/database/migrate.py` | Migración idempotente de columnas `pairing_code_hash` y `pairing_expires_at` |
| `backend/app/schemas/device.py` | `DevicePairRequest`, `DeviceCapacity`, `DevicePublic`, `DeviceProvisioned`, etc. |
| `device/esp32/main.py` | Firmware con emparejamiento serial, `device_config.json` y heartbeat corregido |
| `tests/test_care.py` | Pruebas de asignaciones, permisos y auditoría |
| `tests/test_device_pairing.py` | Pruebas de emparejamiento y límites de dispositivos |
| `docs/conexion-dispositivos.md` | Flujos de conexión ESP32, endpoints, seguridad y ejemplos de uso |
| `docs/estado-sesion.md` | Estado de la versión 3.1.1, datos demo, comandos y pendientes |
| `docs/reporte-dashboard.md` | Investigación y decisiones del panel |
| `README.md` | Instalación, endpoints, cuentas demo y accesibilidad |

---

## Cómo se validó

- `python -m pytest -q`: **56 pruebas aprobadas**.
- `node --check frontend/assets/app.js`: sintaxis correcta.
- Lighthouse en paneles de paciente y administrador: **100 / 100 / 100** (Accesibilidad, Buenas prácticas, SEO), sin fallos.
- Revisión en escritorio (1440×900), móvil (390×844) y zoom equivalente al 200 %: sin desplazamiento horizontal de página.
- Navegación por teclado, foco visible, diálogos con Escape y restauración de sesión verificadas.
- Flujo de conectar, reintentar con código inválido y desvincular probado en navegador contra una base temporal.

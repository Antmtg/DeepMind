# Rediseño del panel BioMonitor O₂T

## 1. Resumen

Este documento registra la investigación de referencia, las decisiones de diseño y la validación del rediseño del panel de BioMonitor O₂T para los cinco roles del sistema: paciente, cuidador, especialista, administrador y auditor.

> **Estado actual (v1.1.4, Deep Mind Apnea):** los dashboards ya se reimplementaron en `frontend/assets/app.js` con el tema océano/apnea y tres roles reales (`athlete`/`coach`/`admin`, con aliases heredados por compatibilidad). Cada rol tiene su dashboard propio:
> - **Deportista:** meta semanal con anillo, cronómetro de apnea, tablas CO₂/O₂, plan del entrenador, respiración guiada, feed de actividad, récords reales, calendario de 56 días, zonas FC y carga aguda/crónica.
> - **Entrenador:** KPIs, plantilla de deportistas, sesiones recientes, formulario de asignación de planes y tarjetas de planes con archivado.
> - **Administrador:** KPIs de sesiones/planes, gráficas de roles/planes/actividad y sección de auditoría con filtros y exportación CSV.
> El backend expone `/api/sessions` y `/api/plans` con permisos por rol, resúmenes de sesiones y eventos de auditoría (`APNEA_SESSION_*`, `TRAINING_PLAN_*`). El documento conserva su valor como referencia de diseño y accesibilidad; la temperatura no aparece en la interfaz web.

El objetivo fue convertir el panel en una herramienta comprensible para personas mayores o con poca familiaridad tecnológica, sin perder las capacidades técnicas del proyecto: autenticación, RBAC, dispositivos ESP32, mediciones, auditoría y pruebas de permisos.

La página de bienvenida y el inicio de sesión se conservaron. El rediseño se concentró en el panel posterior al acceso y en la incorporación de vínculos reales entre pacientes y sus cuidadores o especialistas.

## 2. Alcance

- Un solo rediseño coherente para los cinco perfiles.
- Lenguaje directo, en segunda persona («tú»), sin diagnóstico ni promesas médicas.
- Datos de ejemplo identificados como tales en todo el panel.
- Estados visuales claros: **En rango**, **Para revisar**, **Necesita atención**, **Sin lectura** y **Sin lectura reciente**.
- Asignaciones reales paciente–cuidador y paciente–especialista.
- Panel técnico de RBAC conservado, pero dentro de **Detalles técnicos**, cerrado por defecto.
- Accesibilidad como requisito de producto, no como ajuste posterior.

## 3. Investigación de competidores y referencias

| Referencia | Qué se observó | Decisión aplicada |
|---|---|---|
| [Omron Connect](https://omronconnect.com/) | Prioriza las últimas mediciones, el estado de sincronización y el historial. La información secundaria queda en segundo plano. | Tarjetas de signos vitales con valor grande, estado y fecha de la última lectura. El historial aparece después del resumen. |
| [CareSimple](https://www.caresimple.com/) | Los equipos de cuidado trabajan con pacientes asignados, alertas y una bandeja de seguimiento. | Vínculos paciente–cuidador/especialista y una vista de «Mis pacientes» con estado y alertas en lenguaje llano. |
| [GrandPad](https://www.grandpad.net/) | Diseño senior-first: botones grandes, texto legible, acciones evidentes y acompañamiento familiar. | Tipografía base de 18 px, objetivos táctiles de 48 px, navegación simple y ayuda contextual. |
| [MyChart](https://www.mychart.org/) | Separa la información del paciente de la de sus representantes o cuidadores. | Acceso por rol y por asignación: un cuidador solo ve a los pacientes que tiene vinculados. |
| [Optimize Health](https://optimize.health/) y [HRS](https://www.hrshealthcare.com/) | Los programas de monitoreo remoto usan colas de revisión, estados y priorización; no solo gráficas. | Resumen con personas que requieren revisión, etiquetas de estado y detalle por paciente. |
| [AARP: portales de pacientes](https://www.aarp.org/health/health-care/patient-portals/) | La confianza depende de lenguaje claro, privacidad visible y pasos siguientes concretos. | Explicaciones breves, aviso de datos de ejemplo, notas de privacidad y recomendaciones sin lenguaje alarmista. |
| [W3C WAI: usuarios mayores](https://www.w3.org/WAI/older-users/) | Texto redimensionable, contraste, navegación predecible y tolerancia a errores. | Preferencias de tamaño de texto, alto contraste, movimiento reducido y mensajes de error recuperables. |
| [NN/g: diseño para personas mayores](https://www.nngroup.com/articles/designing-for-seniors/) | Evitar jerga, gestos ocultos y controles pequeños; preferir instrucciones explícitas. | Controles etiquetados, formularios con ayuda, botones visibles y ninguna acción que dependa solo de un gesto. |
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Reflow, foco visible, tamaño de objetivo, contraste, etiquetas y movimiento. | Se verificaron estos criterios con navegación por teclado, zoom, Lighthouse y revisión manual. |

### Conclusiones de la investigación

1. **La última lectura manda.** El usuario necesita responder rápido: «¿cómo está la persona?», «¿cuándo se midió?» y «¿qué hago ahora?».
2. **Un estado no es un diagnóstico.** Las etiquetas deben describir la lectura, no afirmar una enfermedad.
3. **El acompañamiento necesita vínculos explícitos.** Un cuidador o especialista no debería adivinar qué pacientes le corresponden.
4. **La administración debe ser deliberada.** Editar un sensor o quitar un acceso son acciones con consecuencias; requieren confirmación y explicación.
5. **La accesibilidad se nota en los detalles.** Tamaño del texto, contraste, foco visible, mensajes de error y navegación por teclado importan más que una estética llamativa.

## 4. Decisiones de diseño

### 4.1 Un shell común, contenido por rol

Todos los paneles comparten:

- Barra lateral en escritorio y navegación inferior en móvil.
- Encabezado con saludo, rol, actualización, ayuda, accesibilidad y cuenta.
- Área principal `#dash-content` que cambia según el rol.
- Diálogos nativos para ayuda, cuenta, accesibilidad, detalle de paciente, edición de sensor y confirmaciones.
- Aviso permanente de **Datos de ejemplo**.
- Pie con privacidad y términos.

La navegación se adapta al rol, pero no se muestran secciones que el usuario no puede usar.

### 4.2 Contenido por perfil

| Rol | Contenido principal |
|---|---|
| Paciente | Últimos signos vitales, alertas en lenguaje llano, historial, sensores y recomendaciones. |
| Cuidador | Personas asignadas, estado general, signos vitales, alertas y detalle de cada paciente. |
| Especialista | Pacientes asignados, lectura más reciente, sensores, historial y recomendaciones de revisión. |
| Administrador | Resumen del sistema, cuentas (solo lectura), sensores (editar/activar/desactivar) y vínculos (crear/desactivar). |
| Auditor | Resumen de actividad, filtros por resultado/acción, tabla de eventos y exportación CSV. |

### 4.3 Lenguaje y estados

Se evitó el lenguaje clínico innecesario y las afirmaciones médicas. Ejemplos:

- «El oxígeno está en 93%. Está un poco bajo. Observa cómo te sientes y consulta si sigue así.»
- «Una alerta no es un diagnóstico.»
- «No cambies medicamentos ni dosis por tu cuenta.»

Los estados usan texto además de color:

- **En rango**: dentro de los valores de referencia.
- **Para revisar**: un poco fuera de rango; observar y volver a medir.
- **Necesita atención**: fuera de rango de forma importante; buscar ayuda.
- **Sin lectura**: el sensor no tiene mediciones.
- **Sin lectura reciente**: la última lectura es antigua.

### 4.4 Datos de ejemplo

La demo se identifica en la barra lateral, en el encabezado y en las tablas. Los datos sembrados permiten mostrar tres situaciones distintas:

- Sensor de la sala: lectura normal.
- Sensor del dormitorio: lectura para revisar.
- Sensor de reserva: sin lecturas.

Los tres sensores pertenecen al paciente demo. El cuidador y el especialista tienen un vínculo activo con ese paciente.

### 4.5 Panel técnico

El panel de pruebas RBAC y respuesta JSON se conserva dentro de **Detalles técnicos**, cerrado por defecto. Así sigue disponible para la evaluación académica sin competir con la información de salud.

### 4.6 Administración sin creación de cuentas

En esta iteración no se crean usuarios nuevos. El administrador puede:

- Consultar las cuentas y sus roles.
- Editar nombre, ubicación y estado de un sensor.
- Activar o desactivar un sensor.
- Crear un vínculo paciente–cuidador o paciente–especialista.
- Desactivar un vínculo y consultar los inactivos.

Las acciones destructivas o sensibles piden confirmación y explican la consecuencia.

## 5. Vínculos de cuidado

### 5.1 Modelo

La tabla `care_assignments` relaciona un paciente con un miembro del equipo:

| Campo | Descripción |
|---|---|
| `id` | Identificador del vínculo. |
| `patient_id` | Usuario con rol `patient`. |
| `member_id` | Usuario con rol `caregiver` o `specialist`. |
| `relationship` | Tipo de vínculo: `caregiver` o `specialist`. |
| `is_active` | Si el vínculo está vigente. |
| `created_at` | Fecha de creación en UTC. |

Restricciones:

- Un par paciente–miembro solo puede existir una vez.
- El tipo de vínculo debe coincidir con el rol del miembro.
- Un usuario no puede asignarse a sí mismo.
- Desactivar un vínculo no borra el historial.
- Un vínculo inactivo se puede reactivar creando de nuevo el mismo par.

### 5.2 Reglas de acceso

- El paciente ve sus propios dispositivos y mediciones.
- El cuidador y el especialista solo ven pacientes con un vínculo activo.
- El administrador ve todos los dispositivos y vínculos, pero no las mediciones clínicas desde el panel.
- El auditor no ve datos clínicos; solo eventos de auditoría.
- La gestión de dispositivos y vínculos es exclusiva del administrador.

### 5.3 Endpoints de cuidado

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| `GET` | `/api/care/patients` | Cuidador, especialista | Pacientes con vínculo activo. |
| `GET` | `/api/care/patients/{patient_id}` | Cuidador, especialista | Detalle, sensores y lecturas del paciente asignado. |
| `GET` | `/api/care/assignments?include_inactive=` | Administrador | Lista de vínculos. |
| `POST` | `/api/care/assignments` | Administrador | Crea o reactiva un vínculo. |
| `DELETE` | `/api/care/assignments/{id}` | Administrador | Desactiva un vínculo. |

## 6. Cambios de backend relevantes

- `DevicePublic` ya no expone `api_key`; solo incluye datos seguros y el nombre del propietario.
- La creación, edición y eliminación de dispositivos es exclusiva del administrador.
- El acceso al detalle, historial y última medición de un dispositivo respeta la propiedad y las asignaciones activas.
- `GET /api/devices/{id}/measurements` acepta `limit` entre 1 y 200.
- `GET /api/audit` acepta `status`, `action` y `offset`, además de `limit`.
- La temperatura distingue la fuente: corporal (`esp32`/`simulator`) o referencia del sensor (`sensor_die`).
- Las fechas de mediciones se guardan y muestran en hora local; las fechas de auditoría, usuarios y vínculos se guardan en UTC y se convierten a hora local al serializar.

## 7. Accesibilidad

### 7.1 Medidas implementadas

- Texto base de 18 px, con preferencias **Normal**, **Grande** (20 px) y **Muy grande** (23 px).
- Objetivos táctiles principales de 48 × 48 px como mínimo.
- Enlaces de salto al contenido y al panel.
- Foco visible de 3 px en botones, enlaces, campos y controles de navegación.
- Navegación por teclado y diálogos nativos con manejo de Escape.
- Etiquetas `aria-label`, `aria-current`, `aria-pressed`, `aria-live` y `role="status"` donde corresponde.
- Tablas con `caption`, encabezados `scope="col"` y celdas legibles.
- Preferencia de alto contraste con bordes y texto reforzados.
- Preferencia de movimiento reducido y respeto a `prefers-reduced-motion`.
- Reflow sin desplazamiento horizontal de página a 720 px de ancho (equivalente a 200 % de zoom en una pantalla de 1440 px).
- Las tablas anchas se desplazan dentro de su propio contenedor, no en toda la página.
- Mensajes de error en lenguaje claro y con foco en el campo problemático.

### 7.2 Contraste

Se usaron combinaciones de texto oscuro sobre fondos claros y texto blanco sobre la barra lateral oscura. Los estados no dependen solo del color: incluyen texto y, en tablas, un punto con etiqueta.

Lighthouse no reportó fallos de contraste en los paneles evaluados.

## 8. Validación realizada

### 8.1 Pruebas automatizadas

```text
python -m pytest -q
35 passed
```

Incluyen autenticación, permisos por rol, dispositivos, asignaciones, acceso a pacientes, auditoría y serialización de fechas.

### 8.2 Navegación y acciones verificadas

- Bienvenida → demo → inicio de sesión → panel → cierre de sesión.
- Restauración de sesión al recargar.
- Panel de paciente con lecturas, alertas, historial y sensores.
- Panel de cuidador con paciente asignado y detalle.
- Panel de especialista con paciente asignado y detalle.
- Panel de administrador con usuarios, sensores y vínculos.
- Edición de un sensor y restauración de sus datos.
- Desactivación y activación de un sensor.
- Creación, desactivación y reactivación de un vínculo.
- Intento de vínculo duplicado con mensaje claro.
- Filtro de vínculos inactivos.
- Panel de auditoría con filtros por resultado y acción.
- Estado vacío de auditoría y limpieza de filtros.
- Exportación CSV con 41 eventos y codificación UTF-8.
- Diálogo de ayuda, cuenta y accesibilidad.
- Preferencias de texto, contraste y movimiento, incluido restablecer.
- Panel técnico RBAC: paciente recibe HTTP 403 en `/api/users` y el panel lo muestra como acceso rechazado.

### 8.3 Diseño y zoom

| Escenario | Resultado |
|---|---|
| Escritorio 1440 × 900 | Barra lateral visible, navegación inferior oculta, sin desbordamiento de página. |
| Zoom equivalente a 200 % (720 × 450) | Sin desbordamiento horizontal; navegación inferior visible; contenido reflow. |
| Móvil 390 × 844 | Navegación inferior visible; tablas con desplazamiento interno; sin desplazamiento horizontal de página. |
| Movimiento reducido | Animaciones y transiciones desactivadas; `prefers-reduced-motion` respetado. |
| Teclado | Foco visible de 3 px; controles principales de 48 px; diálogos cerrables con Escape. |

### 8.4 Lighthouse

Paneles de paciente y administrador:

| Categoría | Resultado |
|---|---|
| Accesibilidad | 100 |
| Buenas prácticas | 100 |
| SEO | 100 |
| Fallos reportados | 0 |

## 9. Limitaciones y siguientes pasos

- No se crean cuentas desde la interfaz en esta iteración.
- No hay mensajería, notificaciones push ni recordatorios.
- La asignación se desactiva; la reactivación se hace creando de nuevo el mismo par.
- Los datos demo no sustituyen una validación clínica ni hardware real.
- Las tablas conservan desplazamiento horizontal interno en móvil; es una decisión deliberada para no perder columnas.
- Próximos pasos posibles: creación controlada de cuentas, historial de cambios de vínculos, notificaciones y pruebas con usuarios mayores.

## 10. Archivos principales

- `frontend/index.html`: shell del panel, diálogos y panel técnico.
- `frontend/assets/styles.css`: sistema visual, estados, responsive y accesibilidad.
- `frontend/assets/app.js`: navegación, carga por rol, administración, auditoría y preferencias.
- `backend/app/models/assignment.py`: modelo de vínculos.
- `backend/app/services/care_service.py`: consultas y reglas de acceso.
- `backend/app/api/routes/care.py`: endpoints de cuidado.
- `backend/app/services/device_service.py`: acceso a dispositivos según rol y asignación.
- `backend/app/database/seed.py`: usuarios, sensores, vínculos y mediciones demo.
- `tests/test_care.py`: pruebas de asignaciones, permisos y auditoría.

## 11. Conclusión

El panel quedó organizado alrededor de tres preguntas: **cómo está la persona**, **qué lectura lo muestra** y **qué puedo hacer ahora**. La incorporación de vínculos reales hace que «Mis pacientes» signifique algo, y la separación entre datos clínicos, administración y auditoría reduce el riesgo de acciones accidentales.

La validación automática, la revisión en navegador y Lighthouse respaldan la implementación. El resultado es una base sólida para una siguiente iteración centrada en notificaciones, creación de cuentas y pruebas con personas mayores.

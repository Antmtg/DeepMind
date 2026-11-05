# Presentación final — BioMonitor O₂T

**Formato:** 12 diapositivas + demostración en vivo.  
**Duración sugerida:** 10–12 minutos de exposición y 5 minutos de preguntas.  
**Integrantes:** [Completar]  
**Fecha:** [Completar]

---

## Diapositiva 1 — Portada

**BioMonitor O₂T**  
Monitoreo de signos vitales con ESP32, separación por usuario y auditoría.

- Integrantes: [Nombres]
- Materia: Programación 5
- Docente: [Nombre]
- Fecha: [Fecha]

**Nota para el expositor:** abrir el panel ya iniciado en la sesión del paciente
para que la demo esté lista.

---

## Diapositiva 2 — Problema y objetivo

**Problema:** una lectura de salud sin fecha, origen ni control de acceso puede
llevar a decisiones equivocadas.

**Objetivo:** recibir datos de dos ESP32, separarlos por usuario, mostrar su
estado y conservar evidencia de auditoría.

- ¿El dato es actual?
- ¿De qué sensor viene?
- ¿Sigue conectado?
- ¿Quién puede verlo?

---

## Diapositiva 3 — Arquitectura

```text
ESP32 / simulador
   │  X-Device-Api-Key
   ▼
FastAPI ──► SQLite
   │
   ├── JWT + RBAC
   ├── Dispositivos y mediciones
   ├── Vínculos de cuidado
   ├── Auditoría
   └── Frontend HTML/CSS/JS
```

**Mensaje clave:** el servidor decide permisos y propietario; el frontend solo
presenta.

---

## Diapositiva 4 — Seguridad implementada

- Contraseñas con **Argon2id**.
- Sesión con **JWT en cookie HttpOnly**.
- **RBAC** en todas las rutas sensibles.
- Credenciales de dispositivo con **HMAC-SHA256**.
- Código de emparejamiento temporal y de un solo uso.
- Propietario desde la base de datos, nunca desde el payload.
- Auditoría sin contraseñas, tokens ni payloads.

**Mensaje clave:** no confiamos en el cliente ni en el cuerpo del mensaje.

---

## Diapositiva 5 — Dos usuarios, dos dispositivos

| Dispositivo | Dueño | Demostración |
|---|---|---|
| `ESP32-O2T-01` | Paciente Demo | Sesión A |
| `ESP32-O2T-02` | Paciente Demo Dos | Sesión B |

- Cada sensor tiene su propia `api_key`.
- Cada usuario ve solo su sensor y su historial.
- El simulador envía a ambos a la vez con `source="simulator"`.
- La ingesta sin vincular se rechaza con `409`.

**Demo:** mostrar las dos ventanas y el historial separado.

---

## Diapositiva 6 — Origen y estados del dato

**Orígenes visibles:**

- `ESP32 (sensor real)`
- `ESP32 · temp. interna` (no corporal)
- `Simulador (datos simulados)`
- `Datos de ejemplo`

**Estados:**

- Recibiendo datos (≤ 15 s)
- En línea, sin lectura nueva (≤ 90 s)
- Desconectado (> 90 s)
- Desactivado
- Sin lecturas

**Mensaje clave:** el panel nunca confunde una simulación con una medición real.

---

## Diapositiva 7 — Historial y gráficas

- Selector de 10, 30, 60 o 100 lecturas.
- Tres gráficas SVG: SpO₂, pulso y temperatura.
- Eje temporal, unidad y banda de referencia.
- Resumen de mínimo, máximo y último valor.
- Descripción accesible para lectores de pantalla.
- La temperatura interna del sensor se excluye de la gráfica corporal.

**Demo:** cambiar el rango y mostrar la actualización.

---

## Diapositiva 8 — Frecuencias y latencia

| Etapa | Valor |
|---|---|
| Muestreo PPG | 100 Hz durante 4 s |
| Envío | cada 5 s |
| Heartbeat | cada 60 s |
| Refresco del panel | cada 10 s |
| Dato en vivo | ≤ 15 s |
| Enlace activo | ≤ 90 s |

**Latencia observada:** 0–10 s entre la ingesta y el panel, más red.

**Mensaje clave:** los intervalos están documentados y son configurables.

---

## Diapositiva 9 — Resultados

- **62 pruebas automáticas aprobadas.**
- Login/logout, RBAC y aislamiento verificados.
- Dos dispositivos simultáneos con datos separados.
- Historial y gráficas en paciente, cuidador y especialista.
- Administrador con estados de contacto.
- Auditoría con accesos, rechazos y eventos de dispositivo.
- Firmware con MAX30102/DS18B20 implementado.
- Validación física pendiente.

---

## Diapositiva 10 — Correcciones importantes

1. Claves de dispositivo en texto plano → **HMAC-SHA256**.
2. Datos demo marcados como `esp32` → **`demo`**.
3. Ingesta sin dueño permitida → **rechazo 409 + auditoría**.
4. Historial del dueño anterior visible → **filtro por dueño actual**.
5. Firmware aleatorio por defecto → **lectura real o nada**.
6. Sin gráficas → **SVG con referencia y resumen accesible**.
7. Refresco apagado → **10 s por defecto**.

---

## Diapositiva 11 — Limitaciones y trabajo futuro

- Validar MAX30102 y DS18B20 con hardware definitivo.
- Calibrar SpO₂ contra un oximétro de referencia.
- Grabar video de respaldo.
- Agregar notificaciones y aplicación móvil.
- Migrar a PostgreSQL si aumenta la concurrencia.
- Crear cuentas desde la interfaz con invitación.

**Mensaje clave:** el prototipo es funcional y seguro; la validación clínica es
un paso separado.

---

## Diapositiva 12 — Conclusiones y cierre

- El servidor es la autoridad de permisos y asociación.
- Cada lectura conserva su origen y su fecha.
- Dos usuarios y dos dispositivos conviven sin mezclar datos.
- El panel responde: ¿qué?, ¿cuándo?, ¿de dónde?, ¿sigue conectado?
- La documentación y las pruebas respaldan la entrega.

**Cierre:** “No mostramos un dato sin decir de dónde viene ni cuándo llegó.”

**Preguntas.**

---

## Guion de demostración (5 minutos)

1. **Sesión A:** paciente 1, sensor `ESP32-O2T-01`, estado “Recibiendo datos”.
2. **Sesión B:** paciente 2, sensor `ESP32-O2T-02`, datos distintos.
3. Mostrar la tabla: origen `Simulador (datos simulados)`.
4. Cambiar el historial a 60 lecturas.
5. Detener el simulador y esperar 90 s: estado “Desconectado”.
6. Reiniciar el simulador: vuelve “Recibiendo datos”.
7. Abrir cuidador y ver el detalle del paciente asignado.
8. Abrir administrador y mostrar estados de los sensores.
9. Abrir auditoría y filtrar por `DEVICE_DATA_REJECTED`.
10. Cerrar con la idea central: dato con origen, fecha y control de acceso.

## Checklist antes de exponer

```text
[ ] Servidor en 0.0.0.0:8100
[ ] .env con SECRET_KEY y DEVICE_PROVISIONING_KEY
[ ] python simulator/prepare_demo.py ejecutado
[ ] Dos sesiones de navegador listas
[ ] Simulador o ESP32 encendidos
[ ] Gráficas visibles
[ ] Video de respaldo grabado
[ ] PDF y PPTX en el equipo
```

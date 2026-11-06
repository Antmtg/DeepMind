# Benchmark de páginas de bienvenida y plan de mejora

## BioMonitor O₂T

**Versión:** 1.0  
**Fecha:** 2 de noviembre de 2026  
**Alcance:** 15 experiencias de bienvenida de apps de salud, monitoreo remoto, dispositivos conectados y bienestar.  
**Entregable:** diagnóstico de la página actual, benchmark, propuesta de nueva página de bienvenida y backlog priorizado.

> **Estado actual (v1.1.4, Deep Mind Apnea):** esta página de bienvenida ya se implementó en `frontend/index.html` con el tema océano/apnea, tres roles reales (`athlete`, `coach`, `admin`), auto-login de demo con credenciales precargadas, una demo interactiva sin login (cronómetro de retención y respiración 4-4-4-4 con récord en `localStorage`), sección de características y comparativa frente a Strava/MySwimPro/Fathom. El documento conserva su valor como benchmark y referencia de diseño; la implementación final respeta la paleta azules-oscuros/blanco/negro y no muestra temperatura en la interfaz web.

---

## 1. Resumen ejecutivo

La página actual de BioMonitor O₂T es, en la práctica, una **pantalla de acceso con un mensaje de seguridad**. Está bien construida visualmente y transmite confianza, pero responde a la pregunta “¿cómo entro?” antes que a las preguntas que se hace alguien que llega por primera vez:

- ¿Qué hace esta aplicación?
- ¿Para quién es?
- ¿Qué problema me resuelve?
- ¿Qué pasa si entro?
- ¿Por qué debería confiarle información de salud?

El benchmark de 15 apps similares muestra un patrón consistente: las mejores páginas de bienvenida **venden el resultado antes que el login**. Presentan una promesa clara, muestran el producto, segmentan por necesidad o rol, explican la confianza con hechos concretos y ofrecen una acción de bajo compromiso —una demo, un quiz, una evaluación de elegibilidad o un recorrido guiado— antes de pedir credenciales.

### Recomendación central

Convertir la página actual en una **página pública de bienvenida** con esta secuencia:

1. **Promesa:** qué es BioMonitor O₂T y qué gana la persona.
2. **Prueba:** un panel de signos vitales visible, con datos simulados.
3. **Cómo funciona:** tres pasos claros.
4. **Para quién:** los cinco roles y lo que cada uno puede hacer.
5. **Confianza:** Argon2id, JWT, RBAC y auditoría explicados en lenguaje humano.
6. **Acción:** “Probar la demo” como CTA principal e “Iniciar sesión” como secundario.
7. **Respaldo:** preguntas frecuentes, privacidad, términos y aviso de proyecto académico.

### Hallazgos principales

1. **La página actual no explica el producto.** El H1 “Tu información. Siempre protegida.” describe seguridad, no monitoreo de signos vitales. Un visitante no descubre que la app mide SpO₂, pulso y temperatura, ni que conecta hasta tres ESP32.
2. **Los cinco roles son un diferenciador invisible.** Paciente, cuidador, especialista, administrador y auditor no aparecen en la bienvenida. En el benchmark, la segmentación por rol o necesidad es una práctica común.
3. **La demo está escondida.** El selector de perfiles vive dentro de un `<details>` y comparte una contraseña visible. Es funcional para clase, pero mala para descubrir el producto y riesgosa si se despliega fuera del entorno académico.
4. **La confianza es genérica.** “Protección” e “Identidad” son promesas abstractas. La app sí tiene controles concretos —Argon2id, cookie JWT `HttpOnly`, RBAC, auditoría— que deberían mostrarse como beneficios verificables.
5. **La accesibilidad está cerca de ser excelente, pero no llega.** Lighthouse marca 96 en accesibilidad por contrastes y nombres accesibles. Con cambios pequeños se puede llegar a 100.
6. **El mejor contenido de bienvenida es el propio panel.** Las apps de dispositivos y wearables muestran el producto desde el primer scroll. BioMonitor O₂T ya tiene un dashboard con signos vitales; conviene usarlo como prueba visual, no ocultarlo detrás del login.
7. **La página necesita un cierre legal y humano.** No hay política de privacidad, términos, contacto ni aviso de que la demo usa datos de ejemplo. En salud, eso no es un detalle decorativo.

> **Idea clave:** la página no necesita “más diseño”; necesita **contar la historia correcta en el orden correcto**. La identidad visual actual es una buena base y conviene conservarla.

---

## 2. Alcance y método

### 2.1 Qué se comparó

Se revisaron 15 experiencias de bienvenida de productos similares, combinando:

- **Landing pública:** promesa, jerarquía, CTA, prueba social, señales de confianza y footer.
- **Primer uso documentado:** cuando el flujo era público, se revisó el onboarding (creación de cuenta, vinculación de dispositivo, permisos, metas).
- **Contenido de soporte:** reseñas, artículos y flujos de onboarding publicados por terceros para entender lo que ocurre después del registro.

La comparación es **cualitativa y exploratoria**. No pretende ser una auditoría de cumplimiento ni una medición estadística de conversión.

### 2.2 Las 15 apps y por qué son relevantes

| Grupo | Apps | Relevancia para BioMonitor O₂T |
|---|---|---|
| Telemedicina y síntomas | Teladoc Health, Ada Health | Cómo convertir una necesidad de salud en una acción clara. |
| Cuidado crónico y monitoreo remoto | Omada Health, Biofourmis, CopilotIQ, Current Health | Cómo explicar acompañamiento, elegibilidad y valor para distintos actores. |
| Dispositivos conectados | Qardio, iHealth, Withings | Cómo conectar hardware, app y datos de salud sin confundir al visitante. |
| Bienestar y wearables | Welltory, Oura, WHOOP, Bearable | Cómo usar aspiración, evidencia, onboarding guiado y confianza. |
| Portal y gestión | MyChart, CareClinic | Cómo ofrecer rutas de acceso, permisos y privacidad en salud. |

### 2.3 Criterios de análisis

Para cada experiencia se observó:

1. **Claridad de la promesa:** ¿se entiende en cinco segundos qué hace y para quién?
2. **CTA:** ¿cuál es la acción principal y qué tan bajo es el compromiso?
3. **Patrón de onboarding:** ¿qué secuencia sigue el usuario?
4. **Confianza:** ¿qué señales concretas aparecen? ¿Privacidad, validación clínica, soporte humano, seguridad técnica?
5. **Accesibilidad y personalización:** ¿el lenguaje y el diseño sirven a pacientes mayores o crónicos? ¿Hay rutas por rol o condición?
6. **Relevancia:** ¿qué se puede adaptar a BioMonitor O₂T sin copiar ni exagerar?

### 2.4 Limitaciones

- Las páginas públicas cambian con frecuencia; los hallazgos corresponden a la versión consultada en noviembre de 2026.
- No todos los onboardings son accesibles sin crear una cuenta o tener un dispositivo.
- No se realizaron pruebas de usabilidad con usuarios reales en esta fase.
- Las afirmaciones de terceros (porcentajes, certificaciones, testimonios) se citan como **observadas**, no como validadas por este equipo.
- Este reporte no sustituye una revisión legal de privacidad, cumplimiento médico o seguridad.

---

## 3. Diagnóstico de la página actual

### 3.1 Ficha de la página

| Elemento | Estado actual |
|---|---|
| URL | `http://127.0.0.1:8100/` |
| Título | “BioMonitor O₂T · Acceso seguro” |
| Meta description | “Acceso seguro al sistema BioMonitor O₂T” |
| Estructura | Split screen: panel izquierdo de seguridad + tarjeta de login a la derecha |
| H1 | “Tu información. **Siempre protegida.**” |
| Subtítulo | “Ingresa a BioMonitor O₂T para consultar las funciones disponibles de acuerdo con tu perfil.” |
| CTA principal | “Entrar al sistema” |
| CTA secundario | Ninguno visible |
| Demo | Selector de cinco perfiles dentro de un `<details>`, con contraseña común `Practica4!` |
| Navegación pública | Solo logo y estado del servidor |
| Legal | Sin enlaces de privacidad, términos o contacto |
| Analítica | No se encontró instrumentación de eventos en el frontend |
| Accesibilidad | Lighthouse 96; contrastes y nombres accesibles con fallos |
| SEO | Lighthouse 100, pero el título y la descripción no comunican el producto |

### 3.2 Lo que funciona y conviene conservar

- **Identidad visual coherente:** paleta verde azulado, tipografía Space Grotesk/DM Sans, tarjetas suaves y estética de tecnología médica.
- **Jerarquía clara:** el formulario se entiende de inmediato y los campos tienen etiquetas visibles.
- **Buenas bases de formulario:** `autocomplete="username"`, `autocomplete="current-password"`, `required`, `minlength`, mensaje con `role="alert"`.
- **Semántica correcta:** `lang="es"`, `header`, `main`, `section`, encabezados y formulario.
- **Tono de seguridad:** la app transmite cuidado y seriedad, algo valioso en salud.
- **Diferenciador real:** la arquitectura de cinco roles, JWT, Argon2id y auditoría no es marketing; es una característica del proyecto.

### 3.3 Brechas frente a una página de bienvenida

| Dimensión | Qué hay hoy | Por qué es un problema | Qué debería haber |
|---|---|---|---|
| Propuesta de valor | “Tu información, siempre protegida” | Describe seguridad, no el beneficio de monitorear signos vitales | H1 con resultado + subtítulo que explique SpO₂, pulso, temperatura y roles |
| Público | “De acuerdo con tu perfil” | No dice cuáles son los perfiles ni qué obtiene cada uno | Sección “Para quién” con los cinco roles |
| Prueba de producto | Ninguna | El visitante no puede imaginar el panel | Vista previa del dashboard con datos simulados |
| Cómo funciona | Cuatro chips del proceso de login | Explica autenticación, no el flujo de monitoreo | Tres pasos: conectar, visualizar, acompañar |
| Confianza | “Identidad”, “Perfil”, “Permisos”, “Protección” | Son abstracciones; no se pueden verificar | Argon2id, JWT, RBAC y auditoría explicados |
| Demo | Escondida en `<details>` | Se pierde el visitante que quiere probar sin registrarse | Selector de rol visible y CTA “Probar la demo” |
| Acceso | Solo login | No hay ayuda, registro ni recuperación | FAQ, contacto y ruta de acceso clara |
| Legal | Nada | En salud, la privacidad debe estar visible antes del login | Privacidad, términos, aviso de datos de ejemplo o simulados |
| SEO | Título y meta de “acceso seguro” | No comunica la categoría del producto | Título y descripción orientados a monitoreo de signos vitales |
| Accesibilidad | 96 | Contrastes y nombres accesibles fallan | Objetivo 100 y WCAG 2.2 AA |

### 3.4 Lectura en cinco segundos

Si alguien ve la página actual durante cinco segundos, lo más probable es que recuerde:

- “Es una app segura.”
- “Hay que iniciar sesión.”
- “Tiene algo que ver con salud, por el color y el nombre.”

Lo que **no** puede saber es:

- que mide oxigenación, frecuencia cardíaca y temperatura;
- que conecta hasta tres dispositivos ESP32;
- que existe un panel para paciente, cuidador, especialista, administrador y auditor;
- que puede probarla con datos de ejemplo;
- qué ocurre si un valor sale de rango.

Esa es la brecha principal. La página actual funciona como puerta, pero no como bienvenida.

### 3.5 Auditoría Lighthouse registrada

| Categoría | Puntaje |
|---|---:|
| Accesibilidad | 96 |
| Buenas prácticas | 100 |
| SEO | 100 |

**Fallos de accesibilidad detectados:**

| # | Elemento | Problema | Criterio | Corrección propuesta |
|---:|---|---|---|---|
| 1 | `.brand small` | Texto de 11 px con `#687580` sobre `#f3f6f4`: **4.34:1**. Necesita 4.5:1. | WCAG 1.4.3 | Usar `--muted-strong: #55636e` (5.69:1) o subir tamaño/peso. |
| 2 | `.intro-panel h1 em` | Titular en `#00a991` sobre `#f3f6f4`: **2.72:1**. Al ser texto grande necesita 3:1. | WCAG 1.4.3 | Usar `--teal-text: #087c70` (4.68:1) para texto; reservar `#00a991` para gráficos. |
| 3 | `.lead` | Texto de 18 px con `#687580` sobre `#f3f6f4`: **4.34:1**. Necesita 4.5:1. | WCAG 1.4.3 | Usar `--muted-strong` y revisar tamaño. |
| 4 | `.flow b` | Números de 10 px en `#00a991` sobre fondo claro: **2.72:1**. | WCAG 1.4.3 | Usar `--teal-text`, subir a 12 px y aumentar peso. |
| 5 | `a.brand` | `aria-label="BioMonitor O2T"` no contiene el texto visible completo (“BioMonitor O₂T · monitoreo seguro”). | WCAG 2.5.3 | Quitar el `aria-label` y dejar que el contenido visible nombre el enlace. |
| 6 | `#toggle-password` | `aria-label="Mostrar contraseña"` no contiene la etiqueta visible “Ver”. | WCAG 2.5.3 | Visible “Mostrar”/“Ocultar” y `aria-label` coherente; añadir `aria-pressed`. |

**Comprobaciones manuales adicionales:**

- No se observó un enlace “Saltar al contenido”.
- No hay un estilo global de `:focus-visible` para enlaces y botones.
- `prefers-reduced-motion` solo cubre algunas animaciones; el símbolo de marca, el pulso del dispositivo y varias transiciones siguen animándose.
- Los botones de demostración tienen padding de 7 px y texto de 10 px; probablemente no alcanzan 44 × 44 px.
- El mensaje de error usa `role="alert"`, pero no está asociado a los campos con `aria-describedby`.
- El botón de mostrar contraseña no anuncia su estado (`aria-pressed`).
- El símbolo de marca animado puede verse como un óvalo fino en ciertos fotogramas; conviene un logotipo estático o una animación más legible.

### 3.6 Observaciones de seguridad y privacidad

**Fortalezas actuales del proyecto:**

- Contraseñas con Argon2id.
- Sesión en cookie `HttpOnly` con JWT.
- `SameSite=strict` y `secure` configurable.
- RBAC para cinco roles.
- Registro de auditoría de inicios de sesión y acciones relevantes.
- Mensaje de error genérico (“Credenciales incorrectas”), sin revelar si el correo existe.

**Riesgos de la bienvenida actual:**

- La contraseña de demostración `Practica4!` está visible en el HTML. Es aceptable en un entorno académico, pero **no debe llegar a producción**.
- No hay aviso de que la demo usa datos de ejemplo.
- No hay política de privacidad ni explicación de quién puede ver los datos.
- No hay advertencia de que la app no sustituye una valoración médica.
- La demo no está separada conceptualmente del acceso real.

---

## 4. Benchmark de 15 páginas de bienvenida

> **Nota:** las promesas se resumen o traducen; no son citas literales salvo cuando aparecen entre comillas. Las señales de confianza se describen tal como se observaron en la versión consultada.

| # | App · categoría | Promesa y CTA observados | Patrón de bienvenida / onboarding | Señal de confianza | Lección para BioMonitor O₂T |
|---:|---|---|---|---|---|
| 1 | **Teladoc Health** · telemedicina | “Connecting you to better health”. CTA para iniciar una consulta y explorar opciones de cuidado. | Landing organizada por necesidad: atención urgente, salud mental, cuidado crónico; CTA persistente y contenido por condición. | Logos de aseguradoras y empleadores, profesionales licenciados, avisos de privacidad. | Vender el resultado (acceso a cuidado) antes del login; segmentar por necesidad, no por funcionalidad. |
| 2 | **Ada Health** · evaluación de síntomas | Evaluación de síntomas gratuita; CTA para comenzar el chequeo. | Flujo conversacional, una sola tarea principal, resultado explicado y siguiente paso claro. | Revisión médica, privacidad y aviso de que no sustituye una consulta. | Reducir la fricción con una acción de bajo compromiso y explicar qué pasa después. |
| 3 | **Omada Health** · cuidado crónico | “Live healthier. Feel better.” CTA para comprobar elegibilidad. | Elegibilidad primero; kit de bienvenida, coaching, metas y acompañamiento humano. | Resultados clínicos, cobertura de empleadores/aseguradoras, equipo de cuidado. | Cualificar al visitante y mostrar el acompañamiento, no solo la app. |
| 4 | **Qardio** · dispositivos conectados | Dispositivos de presión y ECG validados clínicamente, integrados con una app. CTA de compra/consulta. | Producto primero; ecosistema dispositivo-app; soporte y compatibilidad. | Validación clínica, compatibilidad y garantía. | Mostrar hardware y panel juntos; responder “¿qué necesito para empezar?”. |
| 5 | **iHealth** · dispositivos conectados | Salud conectada: dispositivos y app para medir en casa. CTA a catálogo y app. | Catálogo de productos, integración con la app, tutoriales y soporte. | Validación clínica de dispositivos y atención al cliente. | Explicar la compatibilidad sin obligar a registrarse. |
| 6 | **Welltory** · bienestar y HRV | Medir variabilidad cardíaca, energía y estrés; CTA a quiz/descarga. | Ciencia + logos de prensa + prueba social cuantificada + quiz de bajo compromiso. | Investigación, medios y base de usuarios. | Usar evidencia y una CTA de bajo compromiso; no exagerar afirmaciones de salud. |
| 7 | **CareClinic** · tracker de salud | Organizar salud, medicación y síntomas en un solo lugar; CTA a probar la app. | Páginas por condición, cuadrícula de funciones, valoraciones y número de usuarios. | Badges de privacidad/cifrado, reseñas y respaldo de profesionales. | Crear entradas por rol o condición y hacer visible la privacidad; adaptar a los cinco roles. |
| 8 | **Withings** · salud conectada | “Your lifelong health companion.” CTA a medir a diario y explorar dispositivos. | Ecosistema de dispositivos, hábito diario, encuesta propia de impacto positivo. | Encuesta de impacto (87%), dispositivos de grado médico y trayectoria. | Enmarcar el uso a largo plazo y un hábito simple; una métrica clara vale más que diez funciones. |
| 9 | **Bearable** · seguimiento de síntomas | “Feel more in control of your health.” CTA a empezar a registrar. | Beneficio emocional, respaldo clínico, privacidad y funciones de tracking. | Profesionales de salud, promesas de privacidad y control del usuario. | Vender control y tranquilidad; la privacidad puede ser un argumento central, no una nota al pie. |
| 10 | **Oura** · anillo y bienestar | “Wear your best life.” CTA a comprar el anillo y explorar la app. | Aspiracional, historias de miembros, claim de mejora del 86%, integración anillo-app. | Historias reales, investigación y comunidad. | Aspiración + prueba funciona; en salud clínica, priorizar claridad y evidencia sobre lifestyle. |
| 11 | **Biofourmis** · monitoreo remoto | Cuidado conectado en casa; CTA a explorar soluciones. | Landing enterprise, segmentada por stakeholder (sistema de salud, pagador, paciente), evidencia. | Alianzas con sistemas de salud y evidencia clínica. | Segmentar por stakeholder; mostrar valor operativo para especialistas y administradores. |
| 12 | **CopilotIQ** · monitoreo remoto para mayores | Mejor cuidado en casa para condiciones crónicas; CTA a comprobar elegibilidad. | Lenguaje simple, soporte telefónico, pasos asistidos y enfoque en pacientes mayores. | Cobertura Medicare, equipo de cuidado y acompañamiento humano. | Diseñar para adultos mayores: letra grande, lenguaje claro, ayuda humana y menos pasos. |
| 13 | **Current Health** · monitoreo remoto | Atención de nivel hospitalario en casa; CTA a explorar soluciones. | Landing enterprise por caso de uso, resultados y separación de rutas paciente/administrador. | Sistemas de salud, resultados clínicos y tecnología validada. | Casos de uso creíbles y separación clara entre la experiencia del paciente y la del administrador. |
| 14 | **MyChart** · portal del paciente | Acceso a resultados, citas, mensajes y recetas; CTA de activación o registro. | Dos rutas: código de activación o auto-registro; verificación en dos pasos; acceso proxy. | 2FA, cifrado, respaldo del proveedor de salud y ayuda para activar la cuenta. | Ofrecer rutas de acceso claras y explicar los pasos de seguridad; incluir “no tengo código”. |
| 15 | **WHOOP** · wearable de rendimiento | Rendimiento, recuperación y sueño; CTA a membresía. | Onboarding guiado de unas 15 pantallas: cuenta, vinculación del dispositivo, metas, permisos. | Historias de miembros, investigación y valoraciones. | El onboarding debe ser una secuencia con progreso; no saturar la primera pantalla. |

### 4.1 Síntesis por grupo

**Telemedicina y síntomas (Teladoc, Ada).** La entrada no es “crea una cuenta”, sino “resuelve esto que te pasa”. La navegación por necesidad y el CTA de bajo compromiso reducen la barrera. BioMonitor O₂T puede hacer lo mismo con “ver mis signos vitales” o “probar la demo”, en lugar de “entrar al sistema”.

**Cuidado crónico y monitoreo remoto (Omada, Biofourmis, CopilotIQ, Current Health).** Todos explican el acompañamiento humano y la elegibilidad. No venden solo tecnología: venden seguimiento, equipo y tranquilidad. Para BioMonitor O₂T, esto sugiere una sección “Para quién” que muestre el valor para paciente, cuidador y especialista, y otra para administrador/auditor.

**Dispositivos conectados (Qardio, iHealth, Withings).** El hardware y la app se muestran juntos. El visitante entiende qué necesita, cómo se conecta y qué verá. BioMonitor O₂T tiene una ventaja: puede mostrar un panel real con SpO₂, pulso y temperatura, y explicar que acepta hasta tres ESP32.

**Bienestar y wearables (Welltory, Oura, WHOOP, Bearable).** Combinan aspiración, evidencia y onboarding guiado. Oura y WHOOP convierten el primer uso en un recorrido de varios pasos; Welltory y Bearable usan la confianza y el control como argumentos. La lección es que **la bienvenida no termina en el login**: continúa en el primer uso.

**Portal y gestión (MyChart, CareClinic).** MyChart destaca por ofrecer varias rutas de acceso y explicar la verificación. CareClinic por segmentar por condición y mostrar privacidad. BioMonitor O₂T puede adoptar la claridad de rutas y la segmentación por rol.

### 4.2 Patrones que se repiten

| Patrón | Evidencia en el benchmark | Traducción a BioMonitor O₂T |
|---|---|---|
| **Promesa de resultado en cinco segundos** | Teladoc, Omada, Withings, Bearable | H1 orientado al beneficio, no a la seguridad: “Tu salud, a la vista. Tus datos, bajo control.” |
| **CTA principal + alternativa de bajo compromiso** | Omada (elegibilidad), Welltory (quiz), Oura (compra), MyChart (activación) | “Probar la demo” + “Iniciar sesión”. |
| **Segmentación por necesidad o rol** | Teladoc, CareClinic, MyChart, Biofourmis | Sección con los cinco roles y lo que cada uno puede hacer. |
| **Producto visible desde el inicio** | Qardio, iHealth, Oura, WHOOP | Vista previa del panel con SpO₂, pulso, temperatura y estado del dispositivo. |
| **Confianza específica y verificable** | MyChart (2FA), CareClinic (privacidad), Omada (resultados) | Argon2id, JWT, RBAC y auditoría, explicados sin jerga. |
| **Onboarding progresivo** | WHOOP (≈15 pantallas), Oura (≈25 pantallas), MyChart (activación) | Recorrido de demo por rol; no mostrar todas las funciones de golpe. |
| **Lenguaje simple y accesible** | CopilotIQ, MyChart, Bearable | Frases cortas, letra grande, objetivos táctiles de 44 px y español claro. |
| **Prueba social o evidencia** | Oura, Withings, Welltory | Usar solo evidencia real del proyecto; no inventar testimonios ni certificaciones. |

### 4.3 Qué adoptar y qué evitar

**Adoptar:**

- Una promesa de resultado antes del login.
- Una demo visible y de bajo compromiso.
- Segmentación por rol.
- Una vista del producto real.
- Señales de confianza concretas.
- Preguntas frecuentes y footer legal.
- Onboarding guiado después del acceso.

**Evitar:**

- Copiar textos, logos, testimonios o claims de las apps benchmark.
- Afirmar certificaciones que el proyecto no tiene (HIPAA, ISO, FDA, CE).
- Usar lenguaje de diagnóstico o cura.
- Esconder la demo o exigir registro para ver el producto.
- Prometer “datos en tiempo real” si la demo usa datos simulados sin decirlo.
- Animar todo sin respetar `prefers-reduced-motion`.
- Inventar prueba social.

---

## 5. Propuesta de nueva página de bienvenida

### 5.1 Objetivo y embudo

**Objetivo:** que una persona entienda en menos de 10 segundos qué es BioMonitor O₂T, para quién es y qué puede hacer a continuación.

**Embudo:**

```
Visita pública
   ↓
Entiende la promesa y ve el producto
   ↓
Elige “Probar la demo” o “Iniciar sesión”
   ↓
Selecciona un rol (si elige demo)
   ↓
Explora el panel con datos simulados
   ↓
Vuelve al login real o solicita acceso
```

La página debe funcionar para tres públicos:

1. **Paciente o cuidador:** quiere saber qué se mide y cómo se siente usar la app.
2. **Especialista o administrador:** quiere saber si la app encaja en su flujo y qué permisos existen.
3. **Docente, evaluador o compañero de clase:** quiere entender el proyecto rápido y probarlo sin fricción.

### 5.2 Arquitectura de información

| # | Sección | Propósito | Elementos clave |
|---:|---|---|---|
| 1 | Header | Orientar y dar acceso persistente | Logo, navegación, “Iniciar sesión”, “Probar la demo” |
| 2 | Hero | Promesa + prueba | H1, subtítulo, dos CTA, microcopy, panel de signos vitales |
| 3 | Franja de confianza | Reducir ansiedad | Argon2id, JWT, RBAC, auditoría |
| 4 | Cómo funciona | Explicar el flujo | Tres pasos: conectar, visualizar, acompañar |
| 5 | Para quién | Mostrar los cinco roles | Tarjetas de rol con beneficio y alcance |
| 6 | Seguridad | Convertir la promesa en hechos | Identidad, permisos, trazabilidad, datos simulados |
| 7 | Demo | Dar una acción de bajo compromiso | Selector de rol, contraseña de demo, aviso de entorno |
| 8 | FAQ | Resolver objeciones | Qué mide, cuántos dispositivos, quién ve los datos, hardware, límites médicos |
| 9 | CTA final | Cerrar la visita | “Probar la demo” + “Iniciar sesión” |
| 10 | Footer | Legal y soporte | Privacidad, términos, seguridad, contacto, estado del sistema |

### 5.3 Wireframe de referencia

```
┌──────────────────────────────────────────────────────────────────────┐
│ Logo BioMonitor O₂T   Cómo funciona  Para quién  Seguridad  FAQ     │
│                                          [Iniciar sesión] [Demo]    │
├───────────────────────────────────┬──────────────────────────────────┤
│ MONITOREO DE SIGNOS VITALES       │  Panel del paciente              │
│                                   │  ● Dispositivo conectado         │
│ Tu salud, a la vista.             │                                  │
│ Tus datos, bajo control.          │  SpO₂        97%   En rango      │
│                                   │  Pulso       72    bpm           │
│ Oxigenación, frecuencia cardíaca  │  Temperatura 36.5  °C            │
│ y temperatura de hasta tres       │                                  │
│ dispositivos ESP32, en un panel   │  Última lectura: hace 5 s        │
│ claro para cada rol.              │  Datos de demostración           │
│                                   │                                  │
│ [Probar la demo] [Iniciar sesión] │                                  │
│ Datos simulados · Sin hardware    │                                  │
├───────────────────────────────────┴──────────────────────────────────┤
│ Argon2id · JWT · RBAC · Auditoría                                   │
├──────────────────────────────────────────────────────────────────────┤
│ CÓMO FUNCIONA                                                       │
│ 1. Conecta  2. Visualiza  3. Acompaña                               │
├──────────────────────────────────────────────────────────────────────┤
│ PARA QUIÉN                                                          │
│ Paciente | Cuidador | Especialista | Administrador | Auditor        │
├──────────────────────────────────────────────────────────────────────┤
│ SEGURIDAD                                                           │
│ Identidad | Permisos | Trazabilidad | Datos con contexto            │
├──────────────────────────────────────────────────────────────────────┤
│ DEMO                                                                │
│ Elige un rol: [Paciente] [Cuidador] [Especialista] [Admin] [Auditor]│
├──────────────────────────────────────────────────────────────────────┤
│ PREGUNTAS FRECUENTES                                                │
├──────────────────────────────────────────────────────────────────────┤
│ CTA final + Footer legal                                            │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.4 Copy deck en español

#### Header

- **Logo:** BioMonitor O₂T
- **Navegación:** Cómo funciona · Para quién · Seguridad · Preguntas frecuentes
- **Acciones:** Iniciar sesión · Probar la demo

#### Hero

- **Eyebrow:** MONITOREO DE SIGNOS VITALES · ESP32
- **H1:** Tu salud, a la vista. Tus datos, bajo control.
- **Subtítulo:** Oxigenación, frecuencia cardíaca y temperatura de hasta tres dispositivos ESP32, reunidas en un panel claro para paciente, cuidador y especialista.
- **CTA principal:** Probar la demo
- **CTA secundario:** Iniciar sesión
- **Microcopy:** Datos simulados · Sin hardware · Sin instalar nada

#### Panel de vista previa

- **Título:** Panel del paciente
- **Estado:** ● Dispositivo conectado
- **SpO₂:** 97% · En rango
- **Pulso:** 72 bpm · En rango
- **Temperatura:** 36.5 °C · En rango
- **Pie:** Última lectura: hace 5 s · Datos de demostración

> La vista previa debe ser un componente real o una maqueta fiel del dashboard. No usar una ilustración genérica de médicos o teléfonos.

#### Franja de confianza

- **Argon2id:** contraseñas protegidas.
- **JWT:** sesiones verificadas.
- **RBAC:** permisos por rol.
- **Auditoría:** acciones trazables.

#### Cómo funciona

- **Eyebrow:** CÓMO FUNCIONA
- **H2:** Del sensor al panel, en tres pasos.
- **Paso 1 — Conecta tus dispositivos:** Registra hasta tres ESP32. Cada uno envía SpO₂, pulso y temperatura con su propia clave.
- **Paso 2 — Consulta tus signos vitales:** Mira la última lectura, la tendencia reciente y las alertas cuando un valor sale del rango esperado.
- **Paso 3 — Comparte con tu equipo:** Paciente, cuidador y especialista trabajan con la misma información, cada uno con sus permisos.

#### Para quién

- **Eyebrow:** PARA QUIÉN
- **H2:** Un panel para cada rol.
- **Subtítulo:** Cinco roles, una misma información. Cada uno con el acceso que necesita.
- **Paciente:** Consulta tus signos vitales, la tendencia reciente y las alertas de tus dispositivos.
- **Cuidador:** Acompaña a la persona a tu cargo y revisa sus lecturas sin acceder a la administración.
- **Especialista:** Revisa las mediciones y los dispositivos que tenga asignados, según los permisos configurados.
- **Administrador:** Gestiona usuarios, dispositivos y la configuración del sistema.
- **Auditor:** Revisa accesos y cambios para verificar que la información se usó correctamente.
- **Nota:** El alcance exacto de cada rol depende de los permisos configurados. En la versión actual, algunas acciones de especialista y cuidador están marcadas como “disponible en próxima práctica”; el copy de la bienvenida debe presentar solo lo que ya funciona o etiquetarlo como alcance previsto.

#### Seguridad

- **Eyebrow:** SEGURIDAD
- **H2:** Seguridad visible, no solo prometida.
- **Subtítulo:** La protección no es una frase al pie: está en cómo se autentica, se autoriza y se registra cada acceso.
- **Identidad protegida:** Contraseñas con Argon2id y sesiones firmadas con JWT.
- **Permisos por rol:** RBAC para que cada persona vea solo lo que le corresponde.
- **Trazabilidad:** Registro de auditoría de accesos y acciones relevantes.
- **Datos con contexto:** La demo usa datos de ejemplo. En producción, la información de salud requiere consentimiento y políticas de privacidad.
- **Enlace:** Leer la política de privacidad.

#### Demo

- **Eyebrow:** DEMOSTRACIÓN
- **H2:** Pruébalo con datos de ejemplo.
- **Subtítulo:** Elige un rol y entra al panel. No necesitas hardware ni instalar nada.
- **Botones:** Paciente · Cuidador · Especialista · Administrador · Auditor
- **Microcopy:** Contraseña de demostración: `Practica4!` · Solo para esta demo académica.
- **Aviso:** En un despliegue real, la demo se habilita solo en entornos de prueba.

#### FAQ

- **¿Qué mide BioMonitor O₂T?** Oxigenación (SpO₂), frecuencia cardíaca y temperatura corporal.
- **¿Cuántos dispositivos puedo conectar?** Hasta tres ESP32 de forma simultánea.
- **¿Quién puede ver mis datos?** Solo los roles autorizados. Paciente y cuidador ven signos vitales; el administrador gestiona usuarios y dispositivos; el auditor revisa la trazabilidad.
- **¿Necesito hardware para probar la demo?** No. La demo usa datos de ejemplo.
- **¿La app diagnostica o sustituye a un médico?** No. Es una herramienta de monitoreo y apoyo; no sustituye la valoración profesional.
- **¿Cómo se protege mi información?** Con contraseñas Argon2id, sesiones JWT, permisos RBAC y registro de auditoría.
- **¿Puedo usarla en el celular?** Sí. La interfaz se adapta a móvil, tablet y escritorio.

#### CTA final

- **H2:** Tu salud, a la vista. Empieza por la demo.
- **Texto:** Explora el panel con datos de ejemplo y descubre cómo se ve el monitoreo cuando la información está clara y protegida.
- **Botones:** Probar la demo · Iniciar sesión

#### Footer

- **Marca:** BioMonitor O₂T — Proyecto académico de monitoreo de signos vitales con ESP32.
- **Enlaces:** Privacidad · Términos · Seguridad · Contacto · Estado del sistema.
- **Legal:** © 2026 BioMonitor O₂T. Los datos de la demo son de ejemplo.

### 5.5 Dirección visual

La página debe sentirse como una **extensión natural de la app actual**, no como un sitio distinto.

| Elemento | Recomendación |
|---|---|
| Paleta | Conservar `--ink: #08131c`, `--teal: #00a991`, `--lime: #caff68`, `--paper: #f3f6f4`. Añadir `--teal-text: #087c70` y `--muted-strong: #55636e` para texto. |
| Tipografía | Space Grotesk para titulares, DM Sans para cuerpo. H1 `clamp(44px, 6vw, 76px)`, line-height 0.98, letter-spacing -0.04em. |
| Hero | Dos columnas 55/45 en escritorio; una columna en móvil. Máximo 1180 px. |
| Tarjetas | Radio 20–24 px, borde de 1 px, fondo blanco, sombra suave. Evitar sombras fuertes. |
| Botones | Primario oscuro (`--ink`) con texto blanco; secundario con borde. Estado hover/focus visible. |
| Iconografía | SVG inline de 24 px, trazo 1.5. Reemplazar glifos como ✦, ◈, ◎, ⌁ por iconos consistentes. |
| Movimiento | 150–250 ms; pulso solo en el indicador “conectado”; respetar `prefers-reduced-motion`. |
| Imágenes | Capturas reales del panel o maquetas fieles. Evitar fotos de stock genéricas de médicos. |
| Espaciado | 96–120 px entre secciones en escritorio; 56–64 px en móvil. |
| Responsive | Breakpoints en 1024, 850 y 560 px. En móvil, CTA a ancho completo y preview después del titular. |

### 5.6 Tono de voz

- **Claro:** frases cortas, sin jerga innecesaria.
- **Tranquilo:** no alarmar; explicar qué hacer.
- **Humano:** “tu equipo”, “la persona a tu cargo”, “acompañar”.
- **Preciso:** distinguir “monitoreo” de “diagnóstico”.
- **Honesto:** decir “datos simulados” cuando corresponde.

**Evitar:** “revolucionario”, “cura”, “diagnostica”, “100% seguro”, “certificado”, “tiempo real” sin aclarar que la demo es simulada.

---

## 6. Accesibilidad, seguridad y confianza

### 6.1 Correcciones de accesibilidad prioritarias

| Prioridad | Acción | Detalle |
|---|---|---|
| P0 | Corregir contrastes | Usar `#087c70` para texto teal y `#55636e` para texto secundario sobre `#f3f6f4`. Reservar `#00a991` para gráficos y decoración. |
| P0 | Corregir nombres accesibles | Quitar `aria-label` redundante del logo; hacer que “Mostrar”/“Ocultar” coincida con el nombre accesible del botón. |
| P0 | Añadir foco visible | `:focus-visible` con contorno de 3 px y offset de 3 px en todos los interactivos. |
| P0 | Añadir “Saltar al contenido” | Primer elemento enfocable; visible al recibir foco. |
| P1 | Respetar movimiento reducido | Cubrir marca, fondos ambientales, transiciones y scroll. |
| P1 | Asociar errores a campos | `aria-describedby` y `aria-invalid` cuando el formulario falle. |
| P1 | Anunciar estado del botón de contraseña | `aria-pressed` y cambio de texto “Mostrar”/“Ocultar”. |
| P1 | Objetivos táctiles de 44 px | Botones de demo, enlaces del footer y controles del header. |
| P1 | Revisar jerarquía de encabezados | Un solo `h1` por vista; `h2` por sección; no saltar niveles. |
| P2 | Prueba con lector de pantalla | NVDA o VoiceOver en escritorio y móvil. |
| P2 | Prueba con teclado | Recorrer toda la página sin ratón, incluida la demo y el FAQ. |

**Meta:** Lighthouse Accessibility 100, axe sin errores críticos ni serios y cumplimiento razonable de WCAG 2.2 AA.

### 6.2 Tokens de color recomendados

```css
:root {
  --ink: #08131c;
  --paper: #f3f6f4;
  --white: #ffffff;

  /* Decoración y gráficos */
  --teal: #00a991;
  --lime: #caff68;

  /* Texto sobre fondos claros */
  --teal-text: #087c70;   /* 4.68:1 sobre --paper */
  --muted-strong: #55636e; /* 5.69:1 sobre --paper */
  --muted: #687580;       /* solo para texto grande o no esencial */
}
```

> Los ratios se calcularon contra `#f3f6f4`. Si el fondo cambia, hay que volver a verificarlos.

### 6.3 Ejemplos de corrección

**Logo sin nombre accesible duplicado:**

```html
<a class="brand" href="/">
  <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span>
  <span>
    <strong>BioMonitor</strong>
    <small>O₂T · monitoreo seguro</small>
  </span>
</a>
```

**Botón de contraseña coherente:**

```html
<button id="toggle-password" type="button" aria-pressed="false" aria-label="Mostrar contraseña">
  Mostrar
</button>
```

```js
function setPasswordVisibility(visible) {
  password.type = visible ? "text" : "password";
  toggle.textContent = visible ? "Ocultar" : "Mostrar";
  toggle.setAttribute("aria-label", visible ? "Ocultar contraseña" : "Mostrar contraseña");
  toggle.setAttribute("aria-pressed", String(visible));
}
```

**Movimiento reducido:**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

### 6.4 Seguridad y privacidad de la bienvenida

**Demo segura:**

- Mostrar la demo solo si `DEMO_MODE=true` o si el entorno es local/académico.
- No incluir la contraseña `Practica4!` en el HTML de producción.
- Usar datos de ejemplo y un usuario demo separado.
- Limitar intentos de login y registrar los fallos (ya existe auditoría).
- Deshabilitar la demo en el despliegue final o protegerla con una clave de acceso.

**Privacidad visible:**

- Enlace a una política de privacidad en el footer y cerca del formulario.
- Explicar qué datos se recogen: correo, rol, mediciones, dispositivo, auditoría.
- Explicar para qué se usan y cuánto tiempo se conservan.
- Explicar quién puede verlos: paciente, cuidador, especialista, administrador, auditor, según permisos.
- Añadir un aviso de que la demo no contiene datos reales.
- Incluir un correo de contacto para ejercer derechos sobre los datos.

**Aviso médico:**

> BioMonitor O₂T es una herramienta de monitoreo y apoyo. No realiza diagnósticos ni sustituye la valoración de un profesional de la salud. Si un valor sale del rango esperado, busca atención médica.

**Lo que no se debe afirmar:**

- “Cumple HIPAA” si no hay auditoría legal.
- “Certificado por la FDA/CE” si no existe certificación.
- “100% seguro” o “imposible de hackear”.
- “Diagnostica” o “detecta enfermedades”.
- “Tiempo real” si la demo usa datos simulados.

---

## 7. Medición y validación

### 7.1 Métricas de éxito

| Métrica | Definición | Objetivo inicial |
|---|---|---|
| Comprensión de la propuesta | En prueba de 5 segundos, la persona menciona monitoreo de SpO₂/pulso/temperatura | ≥ 80% de participantes |
| Descubrimiento de la demo | Visitas que hacen clic en “Probar la demo” | ≥ 30% |
| Inicio de demo por rol | Personas que eligen un rol y llegan al panel | ≥ 80% de quienes abren la demo |
| Éxito de login | Logins correctos sobre intentos | ≥ 90% en demo |
| Comprensión de privacidad | Personas que pueden explicar quién ve sus datos | ≥ 80% |
| Accesibilidad | Lighthouse Accessibility | 100 |
| axe | Errores críticos/serios | 0 |
| Móvil | Sin scroll horizontal a 320 px | 100% |
| Rendimiento | LCP en 4G | < 2.5 s |
| Rendimiento | CLS | < 0.1 |
| Rendimiento | INP | < 200 ms |

### 7.2 Eventos a instrumentar

Sin invadir la privacidad ni añadir trackers de terceros sin consentimiento:

- `welcome_view`
- `cta_demo_click`
- `cta_login_click`
- `role_demo_select` (con rol)
- `demo_login_success`
- `demo_login_error`
- `faq_open` (con pregunta)
- `privacy_link_click`
- `scroll_depth` (25/50/75/100)

Para un proyecto académico, se puede usar un endpoint propio o almacenamiento local; evitar Google Analytics u otros terceros en una app de salud sin consentimiento explícito.

### 7.3 Prueba de usabilidad sugerida

Con 5 personas (compañeros, docente, alguien no técnico):

1. Muestra la página 5 segundos y pregunta: “¿Qué hace esta app?”
2. Pide: “Encuentra cómo probar la demo”.
3. Pide: “Averigua quién puede ver tus datos”.
4. Pide: “Encuentra qué mide la app y cuántos dispositivos acepta”.
5. Pide: “Inicia sesión como paciente”.
6. Observa dónde se pierden, qué leen y qué ignoran.

**Criterio de éxito:** completar las tareas sin ayuda, entender el propósito y sentirse tranquilos con la privacidad.

---

## 8. Backlog priorizado

### P0 — Necesario para la siguiente iteración

| # | Mejora | Por qué | Esfuerzo | Criterio de aceptación |
|---:|---|---|---|---|
| 1 | Nuevo hero con propuesta de valor y dos CTA | Hoy no se entiende qué hace la app | M | H1 de resultado, subtítulo con SpO₂/pulso/temperatura, CTA demo + login |
| 2 | Vista previa del panel con datos simulados | La prueba visual vende mejor que una lista de funciones | M | Panel con tres métricas, estado del dispositivo y aviso “datos simulados” |
| 3 | Demo visible por rol | La demo es el principal diferenciador y está escondida | S | Cinco botones de rol visibles; credenciales cargadas; foco en “Entrar” |
| 4 | Corregir contrastes y nombres accesibles | Lighthouse 96 y fallos WCAG | S | Lighthouse 100; `axe` sin errores críticos |
| 5 | Sección “Cómo funciona” en tres pasos | Explica el flujo sin jerga | S | Tres pasos con título y descripción |
| 6 | Sección “Para quién” con los cinco roles | Hace visible el RBAC y el valor para cada público | M | Cinco tarjetas con beneficio y alcance |
| 7 | Footer con privacidad, términos y aviso académico | En salud, la confianza empieza por la transparencia | S | Enlaces funcionales y aviso médico |
| 8 | Responsive, foco visible y movimiento reducido | La página debe funcionar en móvil y con teclado | M | 320 px sin scroll horizontal; foco visible; animaciones desactivables |

### P1 — Alto valor

| # | Mejora | Por qué | Esfuerzo | Criterio de aceptación |
|---:|---|---|---|---|
| 9 | Sección de seguridad con hechos concretos | Convierte “protección” en algo verificable | S | Argon2id, JWT, RBAC y auditoría explicados |
| 10 | FAQ con siete preguntas | Resuelve objeciones antes del login | S | Acordeón accesible; enlaces directos |
| 11 | Modo demo seguro | Evita exponer credenciales en producción | M | `DEMO_MODE`; aviso; datos simulados |
| 12 | SEO y metadatos sociales | Mejora la primera impresión al compartir | S | Título, descripción, OG, favicon |
| 13 | Analítica de eventos y prueba de usabilidad | Permite medir y mejorar | M | Eventos registrados; 5 pruebas realizadas |
| 14 | Restauración de sesión | Si el usuario ya inició sesión, no debería ver la bienvenida | M | `GET /api/auth/me` al cargar; redirección al panel |

### P2 — Después de validar

| # | Mejora | Por qué | Esfuerzo |
|---:|---|---|---|
| 15 | Personalización por rol en la URL (`?rol=paciente`) | Facilita demos y campañas | M |
| 16 | Recorrido guiado o video corto | Explica el producto sin leer | L |
| 17 | Registro, recuperación de contraseña y soporte | Completa el ciclo de acceso | L |
| 18 | Internacionalización español/inglés | Amplía el alcance | L |
| 19 | Auditoría WCAG 2.2 AA con lector de pantalla | Calidad y cumplimiento | M |
| 20 | Evidencia real de resultados o testimonios | Prueba social ética | L |

**Estimación:** S ≤ 4 horas · M ≈ 1 día · L ≈ 2–3 días.

---

## 9. Plan de implementación

### Fase 1 — Fundamentos y accesibilidad (1–2 días)

1. Crear `#welcome-view` como vista pública por defecto.
2. Mover el login a `#login-view`, oculto hasta que se elija “Iniciar sesión” o “Probar la demo”.
3. Ajustar tokens de color y estilos de foco.
4. Corregir nombres accesibles del logo y del botón de contraseña.
5. Añadir “Saltar al contenido” y movimiento reducido.
6. Revisar la jerarquía de encabezados.

### Fase 2 — Contenido y producto (2–3 días)

7. Implementar hero, panel de vista previa y franja de confianza.
8. Añadir “Cómo funciona” y “Para quién”.
9. Añadir sección de seguridad.
10. Hacer visible la demo con los cinco roles.
11. Añadir FAQ y CTA final.
12. Añadir footer con privacidad, términos y aviso médico.

### Fase 3 — Validación y pulido (1–2 días)

13. Probar en 320, 390, 768, 1024 y 1440 px.
14. Recorrer con teclado y lector de pantalla.
15. Ejecutar Lighthouse y axe.
16. Probar los cinco roles de demo.
17. Hacer una prueba de usabilidad con 5 personas.
18. Corregir hallazgos y congelar contenido.

### Archivos a modificar

| Archivo | Cambio |
|---|---|
| `frontend/index.html` | Nueva vista de bienvenida, header público, secciones, footer, metadatos. |
| `frontend/assets/styles.css` | Tokens, layout del hero, tarjetas, responsive, foco, movimiento reducido. |
| `frontend/assets/app.js` | Cambio de vistas, demo por rol, foco, `aria-pressed`, restauración de sesión. |
| `backend/app/main.py` | Sin cambios para la SPA; rutas estáticas si se separan privacidad/términos. |
| `docs/` | Este reporte y borradores de privacidad/términos. |
| `README.md` | Actualizar la descripción de la página de bienvenida y el modo demo. |

### Definition of Done

- [ ] La página se entiende en 5 segundos: qué es, para quién y qué hacer.
- [ ] “Probar la demo” es visible y funciona con los cinco roles.
- [ ] “Iniciar sesión” sigue funcionando y conserva el flujo actual.
- [ ] Lighthouse Accessibility = 100.
- [ ] axe sin errores críticos ni serios.
- [ ] Navegación completa con teclado.
- [ ] Sin scroll horizontal a 320 px.
- [ ] `prefers-reduced-motion` respetado.
- [ ] Footer con privacidad, términos y aviso médico.
- [ ] La demo indica si usa datos de ejemplo o simulados.
- [ ] No hay credenciales de producción en el HTML.
- [ ] Copia revisada por el equipo y el docente.

---

## 10. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Lenguaje que suene a diagnóstico médico | Alto | Usar “monitoreo”, “apoyo”, “alerta”; incluir aviso médico; revisión del docente. |
| Exponer credenciales demo en producción | Alto | `DEMO_MODE`, datos simulados, deshabilitar en despliegue final. |
| Datos de salud sensibles | Alto | HTTPS, consentimiento, minimización, RBAC, auditoría, política de privacidad. |
| Afirmaciones de seguridad exageradas | Medio | Mostrar solo controles reales; evitar “100% seguro” y certificaciones inexistentes. |
| Copiar diseño o claims del benchmark | Medio | Usar las apps como referencia de patrones, no de contenido; crear copy propio. |
| Página demasiado larga | Medio | Priorizar hero, cómo funciona, roles, seguridad y demo; mover detalle a FAQ. |
| Animaciones que afectan accesibilidad | Medio | Movimiento reducido, animaciones sutiles y logotipo estático. |
| Falta de tiempo antes de la entrega | Medio | Entregar P0 primero; P1 y P2 después de validar. |

---

## 11. Conclusiones

1. **La página actual es una buena pantalla de login, pero no una buena bienvenida.** Su narrativa es de seguridad, no de producto.
2. **El benchmark confirma un patrón claro:** promesa → prueba → confianza → acción de bajo compromiso → login.
3. **BioMonitor O₂T tiene material para hacerlo bien:** un dashboard real, cinco roles, dispositivos ESP32 y controles de seguridad concretos.
4. **La mejora de mayor impacto no es estética, es de contenido y jerarquía:** explicar qué hace la app, para quién y cómo probarla.
5. **La accesibilidad y la privacidad deben formar parte del diseño desde el inicio,** no ser una revisión final.
6. **La demo debe ser visible, pero segura:** datos simulados, modo demo y credenciales fuera de producción.

**Siguiente paso recomendado:** implementar el P0 (hero, preview, demo visible, accesibilidad, cómo funciona, roles y footer) y validarlo con cinco personas antes de añadir más secciones.

---

## Apéndice A. Fuentes consultadas

> Fecha de consulta: noviembre de 2026. Las páginas pueden cambiar; se citan como referencia del benchmark.

| # | App | URL |
|---:|---|---|
| 1 | Teladoc Health | https://www.teladochealth.com/ |
| 2 | Ada Health | https://ada.com/ |
| 3 | Omada Health | https://www.omadahealth.com/ |
| 4 | Qardio | https://www.qardio.com/ |
| 5 | iHealth | https://www.ihealthlabs.com/ |
| 6 | Welltory | https://welltory.com/ |
| 7 | CareClinic | https://careclinic.io/ |
| 8 | Withings | https://www.withings.com/en-us |
| 9 | Bearable | https://bearable.app/ |
| 10 | Oura | https://ouraring.com/ |
| 11 | Biofourmis | https://biofourmis.com/ |
| 12 | CopilotIQ | https://copilotiq.com/ |
| 13 | Current Health | https://currenthealth.com/ |
| 14 | MyChart | https://www.mychart.org/ |
| 15 | WHOOP | https://www.whoop.com/ |

**Fuentes complementarias sobre onboarding:**

- Flujos públicos de onboarding de WHOOP y Oura en Mobbin (cuenta, vinculación de dispositivo, metas y permisos).
- Páginas de ayuda de MyChart sobre activación de cuenta, verificación en dos pasos y acceso proxy.
- Artículos y reseñas públicas sobre onboarding de apps de salud y wearables.

## Apéndice B. Evidencia de la auditoría actual

| Evidencia | Resultado |
|---|---|
| Lighthouse Accessibility | 96 |
| Lighthouse Best Practices | 100 |
| Lighthouse SEO | 100 |
| Contraste del titular teal | 2.72:1 |
| Contraste del texto secundario | 4.34:1 |
| Nombre accesible del logo | No coincide con el texto visible |
| Nombre accesible del botón de contraseña | No coincide con “Ver” |
| Demo | Oculta en `<details>`; contraseña compartida visible |
| Legal | Sin enlaces de privacidad, términos o contacto |
| Metadatos | Título y descripción centrados en “acceso seguro” |

## Apéndice C. Checklist rápido para la próxima revisión

- [ ] ¿La página dice qué mide la app?
- [ ] ¿Dice para quién es?
- [ ] ¿Muestra el producto?
- [ ] ¿Hay una acción de bajo compromiso?
- [ ] ¿El login sigue siendo fácil de encontrar?
- [ ] ¿Se entienden los cinco roles?
- [ ] ¿La confianza está respaldada por hechos?
- [ ] ¿Hay aviso de datos de ejemplo o simulados?
- [ ] ¿Hay privacidad, términos y contacto?
- [ ] ¿Funciona con teclado y lector de pantalla?
- [ ] ¿Funciona en móvil?
- [ ] ¿Se entiende sin animaciones?
- [ ] ¿Evita afirmaciones médicas exageradas?
- [ ] ¿La demo está protegida fuera del entorno académico?

## Apéndice D. Glosario breve

| Término | Significado |
|---|---|
| **CTA** | Llamada a la acción; el botón o enlace que se espera que la persona pulse. |
| **Onboarding** | Primer uso guiado de la app: cuenta, dispositivo, permisos y metas. |
| **RBAC** | Control de acceso basado en roles; cada rol ve solo lo que le corresponde. |
| **JWT** | Token firmado que identifica una sesión. |
| **SpO₂** | Saturación de oxígeno en sangre. |
| **Lighthouse** | Herramienta de auditoría de accesibilidad, rendimiento y SEO. |
| **axe** | Herramienta automatizada de pruebas de accesibilidad. |

---

**Fin del reporte.**

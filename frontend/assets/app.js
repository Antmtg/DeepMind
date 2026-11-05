const welcomeView = document.querySelector("#welcome-view");
const loginView = document.querySelector("#login-view");
const dashboardView = document.querySelector("#dashboard-view");
const form = document.querySelector("#login-form");
const message = document.querySelector("#form-message");
const apiResult = document.querySelector("#api-result");
const menuToggle = document.querySelector("#menu-toggle");
const primaryNav = document.querySelector("#primary-nav");
const passwordToggle = document.querySelector("#toggle-password");
const loginButton = document.querySelector("#login-button");

let currentDashboard = null;

const roleNames = {
  patient: "Deportista",
  caregiver: "Entrenador",
  specialist: "Entrenador",
  admin: "Administrador",
  administrador: "Administrador de seguridad",
};

const ROLE_VIEW = {
  patient: {
    kicker: "TU SALUD",
    subtitle: "Este es el resumen de tu salud y tus sensores.",
  },
  caregiver: {
    kicker: "ACOMPAÑAMIENTO",
    subtitle: "Revisa a las personas que tienes a tu cuidado.",
  },
  specialist: {
    kicker: "PACIENTES ASIGNADOS",
    subtitle: "Revisa a tus deportistas y sus últimas lecturas.",
  },
  admin: {
    kicker: "ADMINISTRACIÓN",
    subtitle: "Administra usuarios, sensores y vínculos de cuidado.",
  },
  administrador: {
    kicker: "AUDITORÍA",
    subtitle: "Revisa la actividad y los accesos al sistema.",
  },
};

const ROLE_NAV = {
  patient: [
    { id: "resumen", label: "Mi resumen", icon: "home" },
    { id: "lecturas", label: "Mis lecturas", icon: "chart" },
    { id: "sensores", label: "Mis sensores", icon: "device" },
    { id: "ayuda", label: "Ayuda", icon: "help", action: "help" },
  ],
  caregiver: [
    { id: "resumen", label: "Resumen", icon: "home" },
    { id: "deportistas", label: "Mis deportistas", icon: "users" },
    { id: "ayuda", label: "Ayuda", icon: "help", action: "help" },
  ],
  specialist: [
    { id: "resumen", label: "Resumen", icon: "home" },
    { id: "deportistas", label: "Deportistas", icon: "users" },
    { id: "ayuda", label: "Ayuda", icon: "help", action: "help" },
  ],
  admin: [
    { id: "resumen", label: "Resumen", icon: "home" },
    { id: "admin-usuarios", label: "Usuarios", icon: "users" },
    { id: "admin-sensores", label: "Sensores", icon: "device" },
    { id: "admin-asignaciones", label: "Vínculos", icon: "link" },
  ],
  administrador: [
    { id: "resumen", label: "Resumen", icon: "home" },
    { id: "actividad", label: "Actividad", icon: "audit" },
    { id: "ayuda", label: "Ayuda", icon: "help", action: "help" },
  ],
};

const PREF_KEY = "biomonitor.dashboard.prefs.v2";
const AUTO_REFRESH_MS = 10_000;
const LIVE_DATA_WINDOW = 15_000;
const DEVICE_LINK_WINDOW = 90_000;
const DEFAULT_PREFS = {
  textSize: "normal",
  contrast: "normal",
  motion: "normal",
  autoRefresh: true,
};

const prefs = { ...DEFAULT_PREFS };

const dashState = {
  role: null,
  data: null,
  devices: [],
  carePatients: [],
  users: [],
  assignments: [],
  audit: [],
  auditFilters: { status: "", action: "", limit: 50 },
  assignmentsIncludeInactive: false,
  autoRefreshTimer: null,
  toastTimer: null,
  lastUpdated: null,
  historyLimit: 30,
  sources: [],
  detailPatientId: null,
  editingDeviceId: null,
  editingUserId: null,
  confirmResolve: null,
  observer: null,
};

const RECENT_WINDOW = 15 * 60 * 1000;
const ATTENTION_WINDOW = 24 * 60 * 60 * 1000;

const STATUS_INFO = {
  normal: { label: "En rango", className: "status-normal", cardClass: "" },
  review: { label: "Para revisar", className: "status-review", cardClass: "is-review" },
  critical: { label: "Necesita atención", className: "status-critical", cardClass: "is-critical" },
  live: { label: "Recibiendo datos", className: "status-normal", cardClass: "" },
  stale: { label: "En línea, sin lectura nueva", className: "status-review", cardClass: "is-review" },
  disconnected: { label: "Desconectado", className: "status-none", cardClass: "is-none" },
  inactive: { label: "Desactivado", className: "status-none", cardClass: "is-none" },
  no_data: { label: "Sin lectura", className: "status-none", cardClass: "is-none" },
  offline: { label: "Sin lectura reciente", className: "status-none", cardClass: "is-none" },
  info: { label: "Referencia del sensor", className: "status-info", cardClass: "" },
};

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data?.detail;
    const text = Array.isArray(detail)
      ? detail.map((item) => item.msg ?? String(item)).join(" ")
      : detail;
    const error = new Error(text ?? `Error HTTP ${response.status}`);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return { status: response.status, data };
}

function initials(name) {
  const parts = String(name ?? "").trim().split(/\s+/).filter(Boolean);
  const value = parts.slice(0, 2).map((part) => part[0]).join("");
  return (value || "BM").toUpperCase();
}

function firstName(name) {
  return String(name ?? "").trim().split(/\s+/)[0] || "hola";
}

function roleLabel(role) {
  return roleNames[role] ?? "Usuario";
}

function setView(view, { updateHash = true, focus = true } = {}) {
  const changed = document.body.dataset.view !== view;

  welcomeView.classList.toggle("hidden", view !== "welcome");
  loginView.classList.toggle("hidden", view !== "login");
  dashboardView.classList.toggle("hidden", view !== "dashboard");
  document.body.dataset.view = view;

  const titles = {
    welcome: "Deep Mind · Monitoreo de signos vitales",
    login: "Iniciar sesión · Deep Mind",
    dashboard: "Panel · Deep Mind",
  };
  document.title = titles[view];

  closeMobileMenu();

  if (view !== "dashboard") stopAutoRefresh();

  if (updateHash) {
    const hash = view === "login" ? "#acceso" : view === "welcome" ? "#inicio" : "#panel";
    if (window.location.hash !== hash) {
      const method = view === "dashboard" ? "replaceState" : "pushState";
      history[method]({ view }, "", hash);
    }
  }

  if (focus && changed) {
    window.scrollTo({ top: 0, behavior: "auto" });
    const heading =
      view === "welcome"
        ? document.querySelector("#welcome-title")
        : view === "login"
          ? document.querySelector("#login-title")
          : document.querySelector("#dashboard-title");
    heading?.focus({ preventScroll: true });
  }
}

function showWelcome(options = {}) {
  setView("welcome", options);
}

function showLogin(options = {}) {
  setView("login", options);
}

async function showDashboard(data, options = {}) {
  currentDashboard = data;
  dashState.data = data;
  dashState.role = data.user.role;
  setView("dashboard", options);
  renderDashboardShell(data);
  await loadRoleDashboard({ initial: true });
  startAutoRefresh();
}

function renderDashboardShell(data) {
  const role = data.user.role;
  const view = ROLE_VIEW[role] ?? ROLE_VIEW.patient;

  document.querySelector("#dashboard-title").textContent = `Hola, ${firstName(data.user.full_name)}`;
  document.querySelector("#dash-subtitle").textContent = view.subtitle;
  document.querySelector("#dash-kicker").textContent = view.kicker;
  document.querySelector("#role-chip").textContent = roleLabel(role).toUpperCase();
  document.querySelector("#side-name").textContent = data.user.full_name;
  document.querySelector("#side-role").textContent = roleLabel(role);
  document.querySelector("#avatar").textContent = initials(data.user.full_name);
  document.querySelector("#header-avatar").textContent = initials(data.user.full_name);
  document.querySelector("#account-button").setAttribute(
    "aria-label",
    `Abrir tu cuenta: ${initials(data.user.full_name)}`
  );
  document.querySelector("#account-avatar").textContent = initials(data.user.full_name);
  document.querySelector("#account-name").textContent = data.user.full_name;
  document.querySelector("#account-email").textContent = data.user.email;
  document.querySelector("#account-role").textContent = roleLabel(role).toUpperCase();

  renderNav(role);
  updateUpdatedLabel();
  updateAccountUpdated();
}

function renderNav(role) {
  const items = ROLE_NAV[role] ?? [];
  const html = items
    .map((item, index) => {
      const icon = iconFor(item.icon);
      if (item.action === "help") {
        return `<button type="button" class="dash-nav-item" data-open-help>${icon}<span>${escapeHtml(item.label)}</span></button>`;
      }
      const current = index === 0 ? ' aria-current="location"' : "";
      return `<button type="button" class="dash-nav-item" data-scroll="${item.id}"${current}>${icon}<span>${escapeHtml(item.label)}</span></button>`;
    })
    .join("");

  document.querySelector("#dash-nav").innerHTML = html;
  document.querySelector("#bottom-nav").innerHTML = html;
}

function iconFor(name) {
  const open = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">';
  const close = "</svg>";
  const icons = {
    home: '<path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9"/><path d="M9 20v-6h6v6"/>',
    chart: '<path d="M4 19V5"/><path d="M4 19h16"/><path d="m7 15 3-4 3 2 4-6"/>',
    device: '<rect x="5" y="3" width="14" height="18" rx="3"/><circle cx="12" cy="14" r="3"/><path d="M9 7h6"/>',
    users: '<circle cx="9" cy="8" r="3"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16 5.5a3 3 0 0 1 0 5.8"/><path d="M18 14a5 5 0 0 1 3 4.6"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.2 1.2"/><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.2-1.2"/>',
    audit: '<path d="M9 4h6"/><path d="M9 4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2"/><path d="M9 11h6"/><path d="M9 15h6"/><path d="M9 19h4"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 4 2c-.9.7-1.5 1.2-1.5 2.5"/><path d="M12 17h.01"/>',
    drop: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z"/>',
    heart: '<path d="M20.8 5.6a5.5 5.5 0 0 0-7.8 0L12 6.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 22l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z"/>',
    thermometer: '<path d="M14 4v10.5a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/><path d="M12 8v8"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    alert: '<path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 9v5"/><path d="M12 17h.01"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  };
  return `${open}${icons[name] ?? icons.info}${close}`;
}

function loadPrefs() {
  try {
    const saved = JSON.parse(localStorage.getItem(PREF_KEY) ?? "{}");
    if (["normal", "large", "xlarge"].includes(saved.textSize)) prefs.textSize = saved.textSize;
    if (["normal", "high"].includes(saved.contrast)) prefs.contrast = saved.contrast;
    if (["normal", "reduced"].includes(saved.motion)) prefs.motion = saved.motion;
    if (typeof saved.autoRefresh === "boolean") prefs.autoRefresh = saved.autoRefresh;
  } catch {
    /* Las preferencias son opcionales. */
  }
}

function persistPrefs() {
  try {
    localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
  } catch {
    /* Si el navegador bloquea el almacenamiento, la sesión sigue funcionando. */
  }
}

function applyPrefs() {
  document.documentElement.dataset.dashText = prefs.textSize;
  document.body.dataset.dashContrast = prefs.contrast;
  document.body.dataset.dashMotion = prefs.motion;

  document.querySelectorAll("[data-text-size]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.textSize === prefs.textSize));
  });
  document.querySelectorAll("[data-contrast]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.contrast === prefs.contrast));
  });
  document.querySelectorAll("[data-motion]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.motion === prefs.motion));
  });

  const auto = document.querySelector("#auto-refresh");
  if (auto) auto.checked = prefs.autoRefresh;
}

function startAutoRefresh() {
  stopAutoRefresh();
  if (!prefs.autoRefresh || !dashState.role) return;
  dashState.autoRefreshTimer = setInterval(() => {
    if (document.hidden) return;
    if (document.querySelector("dialog[open]")) return;
    loadRoleDashboard({ silent: true });
  }, AUTO_REFRESH_MS);
}

function stopAutoRefresh() {
  if (dashState.autoRefreshTimer) {
    clearInterval(dashState.autoRefreshTimer);
    dashState.autoRefreshTimer = null;
  }
}

function updateUpdatedLabel() {
  const element = document.querySelector("#dash-updated");
  if (!element) return;
  const auto = prefs.autoRefresh
    ? ` · Actualización automática cada ${AUTO_REFRESH_MS / 1000} s`
    : " · Actualización manual";
  element.textContent = dashState.lastUpdated
    ? `Actualizado ${formatDateTime(dashState.lastUpdated)}${auto}`
    : "Aún sin actualizar";
}

function updateAccountUpdated() {
  const element = document.querySelector("#account-updated");
  if (element) {
    element.textContent = dashState.lastUpdated ? formatTime(dashState.lastUpdated) : "—";
  }
}

async function loadSession() {
  try {
    const { data } = await apiFetch("/api/dashboard");
    await showDashboard(data, { updateHash: true, focus: false });
    return true;
  } catch (error) {
    if (error.status !== 401) console.error(error);
    return false;
  }
}

function routeFromHash({ focus = true } = {}) {
  const hash = window.location.hash;

  if (hash === "#acceso") {
    if (currentDashboard) {
      if (document.body.dataset.view !== "dashboard") {
        showDashboard(currentDashboard, { updateHash: false, focus: false });
      }
    } else {
      showLogin({ updateHash: false, focus });
    }
    return;
  }

  if (hash === "" || hash === "#inicio" || hash === "#panel") {
    if (currentDashboard && hash === "#panel") {
      if (document.body.dataset.view !== "dashboard") {
        showDashboard(currentDashboard, { updateHash: false, focus: false });
      }
    } else {
      showWelcome({ updateHash: false, focus });
    }
  }
}

async function logout() {
  currentDashboard = null;
  dashState.role = null;
  stopAutoRefresh();
  try {
    await apiFetch("/api/auth/logout", { method: "POST" });
  } finally {
    window.location.assign("/");
  }
}


async function loadRoleDashboard({ initial = false } = {}) {
  const content = document.querySelector("#dash-content");
  if (!dashState.role) return false;

  content.setAttribute("aria-busy", "true");
  clearDashStatus();
  if (initial) content.innerHTML = loadingMarkup();

  try {
    if (dashState.role === "patient") {
      await loadPatientDashboard();
    } else if (dashState.role === "caregiver" || dashState.role === "specialist") {
      await loadCareDashboard(dashState.role);
    } else if (dashState.role === "admin") {
      await loadAdminDashboard();
    } else if (dashState.role === "administrador") {
      await loadAdministradorDashboard();
    }

    dashState.lastUpdated = new Date();
    updateUpdatedLabel();
    updateAccountUpdated();
    setupScrollSpy();
    return true;
  } catch (error) {
    console.error(error);
    content.innerHTML = errorState(error);
    showDashStatus("No pudimos cargar la información. Revisa tu conexión y vuelve a intentarlo.", "error");
    return false;
  } finally {
    content.setAttribute("aria-busy", "false");
  }
}

function loadingMarkup() {
  return `
    <p class="sr-only">Cargando información…</p>
    <div class="loading-grid" aria-hidden="true">
      <div class="skeleton loading-block"></div>
      <div class="skeleton loading-block"></div>
      <div class="skeleton loading-block"></div>
    </div>`;
}

function errorState(error, title = "No pudimos cargar la información") {
  const message =
    error?.status === 403
      ? "No tienes permiso para ver esta sección."
      : error?.status === 401
        ? "Tu sesión terminó. Vuelve a iniciar sesión."
        : "Revisa tu conexión y vuelve a intentarlo.";
  return `<div class="empty-state" role="alert">
    <div class="empty-icon">${iconFor("alert")}</div>
    <h3>${escapeHtml(title)}</h3>
    <p>${escapeHtml(message)}</p>
    <button type="button" class="dash-button dash-button-primary" data-retry>Volver a intentar</button>
  </div>`;
}

function clearDashStatus() {
  const element = document.querySelector("#dash-status");
  if (!element) return;
  element.classList.add("hidden");
  element.textContent = "";
}

function showDashStatus(text, type = "error") {
  const element = document.querySelector("#dash-status");
  if (!element) return;
  element.textContent = text;
  element.classList.toggle("is-error", type === "error");
  element.classList.toggle("is-ok", type === "ok");
  element.classList.remove("hidden");
}

function showToast(text, type = "ok") {
  const element = document.querySelector("#dash-toast");
  if (!element) return;
  element.textContent = text;
  element.classList.toggle("is-error", type === "error");
  element.classList.remove("hidden");
  clearTimeout(dashState.toastTimer);
  dashState.toastTimer = setTimeout(() => element.classList.add("hidden"), 4500);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return map[character];
  });
}

function parseDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function dateValue(value) {
  return parseDate(value)?.getTime() ?? 0;
}

function formatDateTime(value) {
  const date = parseDate(value);
  if (!date) return "—";
  return date.toLocaleString("es", { dateStyle: "medium", timeStyle: "short" });
}

function formatTime(value) {
  const date = parseDate(value);
  if (!date) return "—";
  return date.toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" });
}

function formatRelative(value) {
  const date = parseDate(value);
  if (!date) return "fecha desconocida";
  const difference = Date.now() - date.getTime();
  if (difference < 0) return "ahora";
  const minutes = Math.floor(difference / 60_000);
  if (minutes < 1) return "hace menos de 1 min";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "hace 1 día";
  if (days < 30) return `hace ${days} días`;
  return date.toLocaleDateString("es", { dateStyle: "medium" });
}

function isWithin(value, milliseconds) {
  const date = parseDate(value);
  if (!date) return false;
  return Math.abs(Date.now() - date.getTime()) <= milliseconds;
}

function unique(values) {
  return [...new Set(values)];
}

function plural(count, singular, pluralForm) {
  return count === 1 ? singular : pluralForm;
}

function numberOrNull(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function tempSource(source) {
  return source === "sensor_die" ? "sensor_die" : "body";
}

function sourceLabel(source) {
  if (source === "simulator") return "Simulador (datos simulados)";
  if (source === "demo") return "Datos de ejemplo";
  if (source === "sensor_die") return "ESP32 · temp. interna";
  if (source === "esp32") return "ESP32 (sensor real)";
  return "Origen desconocido";
}

function sourceSummary(sources) {
  const labels = unique((sources ?? []).filter(Boolean).map(sourceLabel));
  if (!labels.length) return "Todavía no hay un origen de datos registrado.";
  return `${labels.length === 1 ? "Origen de los datos" : "Orígenes de los datos"}: ${labels.join(", ")}.`;
}

function sourceNote(sources) {
  return `<p class="reference-note source-note"><strong>${escapeHtml(sourceSummary(sources))}</strong> Cada lectura conserva el origen con el que fue recibida.</p>`;
}

function metricStatus(type, value, source) {
  const number = numberOrNull(value);
  if (number === null) return "no_data";

  if (type === "spo2") {
    if (number < 90) return "critical";
    if (number < 95) return "review";
    return "normal";
  }

  if (type === "pulse") {
    if (number < 50 || number > 120) return "critical";
    if (number < 60 || number > 100) return "review";
    return "normal";
  }

  if (type === "temp") {
    if (source === "sensor_die") return "info";
    if (number < 35 || number >= 38.5) return "critical";
    if (number < 36 || number >= 37.6) return "review";
    return "normal";
  }

  return "normal";
}

function worseStatus(current, candidate) {
  const order = { normal: 0, info: 0, no_data: 0, review: 1, critical: 2 };
  return (order[candidate] ?? 0) > (order[current] ?? 0) ? candidate : current;
}

function combinedStatusFromVitals(vitals) {
  const statuses = [
    metricStatus("spo2", vitals.spo2),
    metricStatus("pulse", vitals.heart_rate_bpm),
  ].filter((status) => status !== "no_data" && status !== "info");

  return statuses.length ? statuses.reduce(worseStatus, "normal") : "no_data";
}

function alertsFor(vitals) {
  // Sin alertas textuales: solo escala de semáforo (verde/amarillo/rojo).
  return [];
  const spo2 = numberOrNull(vitals.spo2);
  const pulse = numberOrNull(vitals.heart_rate_bpm);
  const temperature = numberOrNull(vitals.temperature_c);
  const source = vitals.temperature_source ?? "body";

  if (spo2 !== null) {
    if (spo2 < 90) {
      alerts.push(`El oxígeno está en ${spo2}%. Es bajo. Busca atención médica ahora.`);
    } else if (spo2 < 95) {
      alerts.push(`El oxígeno está en ${spo2}%. Está un poco bajo. Observa cómo te sientes y consulta si sigue así.`);
    }
  }

  if (pulse !== null) {
    if (pulse < 50) {
      alerts.push(`El pulso está en ${pulse} lpm. Es bajo. Si te sientes mareado o débil, busca atención.`);
    } else if (pulse > 120) {
      alerts.push(`El pulso está en ${pulse} lpm. Es alto. Si tienes mareo, dolor en el pecho o falta de aire, busca atención.`);
    } else if (pulse < 60) {
      alerts.push(`El pulso está en ${pulse} lpm. Está un poco bajo. Si te sientes bien, puede ser normal para ti.`);
    } else if (pulse > 100) {
      alerts.push(`El pulso está en ${pulse} lpm. Está un poco alto. Descansa y vuelve a medir.`);
    }
  }

  if (temperature !== null && source !== "sensor_die") {
    if (temperature < 35) {
      alerts.push(`La temperatura está en ${temperature} °C. Es baja. Abrígate y busca atención si sigues así.`);
    } else if (temperature >= 38.5) {
      alerts.push(`La temperatura está en ${temperature} °C. Es alta. Consulta pronto.`);
    } else if (temperature < 36) {
      alerts.push(`La temperatura está en ${temperature} °C. Está un poco baja.`);
    } else if (temperature >= 37.6) {
      alerts.push(`La temperatura está en ${temperature} °C. Está un poco alta. Observa si tienes otros síntomas.`);
    }
  }

  return alerts;
}

function statusPill(status, label) {
  const info = STATUS_INFO[status] ?? STATUS_INFO.no_data;
  return `<span class="status-pill ${info.className}"><span class="status-dot" aria-hidden="true"></span><span class="sr-only">Estado: </span>${escapeHtml(label ?? info.label)}</span>`;
}

function callout(kind, icon, title, bodyHtml) {
  return `<div class="callout callout-${kind}">
    <span class="callout-icon" aria-hidden="true">${icon}</span>
    <div><strong>${escapeHtml(title)}</strong>${bodyHtml}</div>
  </div>`;
}

function alertListHtml(alerts) {
  if (!alerts?.length) return "";
  return `<ul>${alerts.map((alert) => `<li>${escapeHtml(alert)}</li>`).join("")}</ul>`;
}

function sectionHead(kicker, title, text) {
  return `<div class="dash-section-head">
    <p class="dash-kicker">${escapeHtml(kicker)}</p>
    <h2 tabindex="-1">${escapeHtml(title)}</h2>
    <p>${escapeHtml(text)}</p>
  </div>`;
}

function emptyState({ title, text, actionLabel = "", actionAttr = "", icon = "info" }) {
  const action = actionLabel
    ? `<button type="button" class="dash-button dash-button-primary" ${actionAttr}>${escapeHtml(actionLabel)}</button>`
    : "";
  return `<div class="empty-state">
    <div class="empty-icon">${iconFor(icon)}</div>
    <h3>${escapeHtml(title)}</h3>
    <p>${escapeHtml(text)}</p>
    ${action}
  </div>`;
}

function metricCard(label, value, note) {
  return `<article class="dash-card metric-card">
    <span>${escapeHtml(label)}</span>
    <strong>${escapeHtml(value)}</strong>
    <small>${escapeHtml(note)}</small>
  </article>`;
}

function miniVitals(vitals) {
  if (!vitals) return '<p class="dash-muted">Sin lecturas todavía.</p>';
  return `<div class="mini-vitals">
    <div class="mini-vital"><span>Oxígeno</span><strong>${vitals.spo2 ?? "—"}${vitals.spo2 !== null && vitals.spo2 !== undefined ? "<small>%</small>" : ""}</strong></div>
    <div class="mini-vital"><span>Pulso</span><strong>${vitals.heart_rate_bpm ?? "—"}${vitals.heart_rate_bpm !== null && vitals.heart_rate_bpm !== undefined ? "<small> lpm</small>" : ""}</strong></div>
  </div>`;
}

function vitalCard({ label, value, unit, status, meta, reference, icon }) {
  const info = STATUS_INFO[status] ?? STATUS_INFO.no_data;
  const display = value === null || value === undefined || value === "" ? "—" : escapeHtml(String(value));
  const unitHtml = display !== "—" ? `<small>${escapeHtml(unit)}</small>` : "";
  return `<article class="vital-card ${info.cardClass}">
    <div class="vital-top">
      <p class="vital-label">${escapeHtml(label)}</p>
      <span class="vital-icon">${iconFor(icon)}</span>
    </div>
    <div class="vital-number">${display}${unitHtml}</div>
    ${statusPill(status)}
    <p class="vital-meta">${escapeHtml(meta)}</p>
    <p class="vital-ref">${escapeHtml(reference)}</p>
  </article>`;
}

function measurementsTable(rows, { showDevice = true, caption = "Lecturas registradas. La columna Origen indica la fuente de cada dato." } = {}) {
  if (!rows?.length) {
    return emptyState({
      title: "Sin lecturas",
      text: "Todavía no hay lecturas para mostrar.",
      icon: "chart",
    });
  }

  const deviceHead = showDevice ? '<th scope="col">Sensor</th>' : "";
  const body = rows
    .map((row) => {
      const status = combinedStatusFromVitals({
        spo2: row.spo2,
        heart_rate_bpm: row.heart_rate_bpm,
      });
      const deviceCell = showDevice ? `<td>${escapeHtml(row.device?.name ?? "—")}</td>` : "";
      return `<tr>
        <td><strong>${escapeHtml(formatDateTime(row.measured_at))}</strong><small>${escapeHtml(formatRelative(row.measured_at))}</small></td>
        ${deviceCell}
        <td>${row.spo2 ?? "—"}${row.spo2 !== null && row.spo2 !== undefined ? "%" : ""}</td>
        <td>${row.heart_rate_bpm ?? "—"}${row.heart_rate_bpm !== null && row.heart_rate_bpm !== undefined ? " lpm" : ""}</td>
        <td>${escapeHtml(sourceLabel(row.source))}</td>
        <td>${statusPill(status)}</td>
      </tr>`;
    })
    .join("");

  return `<div class="table-wrap"><table>
    <caption>${escapeHtml(caption)}</caption>
    <thead><tr><th scope="col">Fecha y hora</th>${deviceHead}<th scope="col">Oxígeno</th><th scope="col">Pulso</th><th scope="col">Origen</th><th scope="col">Estado</th></tr></thead>
    <tbody>${body}</tbody>
  </table></div>`;
}

function lastReceptionDate(device, latest) {
  const dates = [parseDate(device?.last_seen), parseDate(latest?.taken_at)].filter(Boolean);
  if (!dates.length) return null;
  return new Date(Math.max(...dates.map((date) => date.getTime())));
}

function deviceStatusInfo(device, latest) {
  if (!device?.is_active) {
    return { key: "inactive", label: "Desactivado" };
  }
  const lastReception = lastReceptionDate(device, latest);
  if (latest && isWithin(latest.taken_at, LIVE_DATA_WINDOW)) {
    return { key: "live", label: "Recibiendo datos" };
  }
  if (lastReception && Date.now() - lastReception.getTime() <= DEVICE_LINK_WINDOW) {
    return { key: "stale", label: "En línea, sin lectura nueva" };
  }
  if (lastReception) {
    return { key: "disconnected", label: "Desconectado" };
  }
  return { key: "no_data", label: "Sin lecturas" };
}

function deviceAdminStatus(device) {
  if (!device?.is_active) return { key: "inactive", label: "Desactivado" };
  const lastSeen = parseDate(device.last_seen);
  if (!lastSeen) return { key: "no_data", label: "Sin contacto" };
  if (Date.now() - lastSeen.getTime() <= DEVICE_LINK_WINDOW) {
    return { key: "live", label: "En línea" };
  }
  return { key: "disconnected", label: "Desconectado" };
}

function sensorCard(item, latest) {
  const { device } = item;
  const status = deviceStatusInfo(device, latest);
  const lastReception = lastReceptionDate(device, latest);
  const dataNote =
    status.key === "live"
      ? "Los datos se están actualizando."
      : status.key === "stale"
        ? "El equipo sigue conectado, pero no hay una lectura nueva."
        : status.key === "disconnected"
          ? "Estos son los últimos datos recibidos; ya no se actualizan."
          : status.key === "inactive"
            ? "El sensor está desactivado; se conserva su historial."
            : "Todavía no se ha recibido ninguna lectura.";
  const owner = device.owner_name ? ` · ${device.owner_name}` : "";
  return `<article class="dash-card sensor-card">
    <div class="sensor-head">
      <div class="sensor-title">
        <span class="sensor-icon">${iconFor("device")}</span>
        <div>
          <h3>${escapeHtml(device.name)}</h3>
          <p class="sensor-sub">${escapeHtml(device.location || "Sin ubicación")} · ${escapeHtml(device.device_id)}${escapeHtml(owner)}</p>
        </div>
      </div>
      ${statusPill(status.key, status.label)}
    </div>
    <dl class="sensor-facts">
      <div><dt>Última recepción</dt><dd>${lastReception ? `${escapeHtml(formatDateTime(lastReception))}<small>${escapeHtml(formatRelative(lastReception))}</small>` : "Sin contacto"}</dd></div>
      <div><dt>Última lectura</dt><dd>${latest ? `${escapeHtml(formatDateTime(latest.taken_at))}<small>${escapeHtml(formatRelative(latest.taken_at))}</small>` : "Sin lecturas"}</dd></div>
      <div><dt>Oxígeno</dt><dd>${latest?.spo2 !== null && latest?.spo2 !== undefined ? `${latest.spo2}%` : "—"}</dd></div>
      <div><dt>Pulso</dt><dd>${latest?.heart_rate_bpm !== null && latest?.heart_rate_bpm !== undefined ? `${latest.heart_rate_bpm} lpm` : "—"}</dd></div>
      <div><dt>Origen</dt><dd>${latest ? escapeHtml(sourceLabel(latest.source)) : "—"}</dd></div>
    </dl>
    <p class="sensor-data-note ${status.key === "live" ? "is-live" : ""}">${escapeHtml(dataNote)}</p>
    <div class="sensor-actions">
      <button type="button" class="dash-button dash-button-danger" data-unpair-device="${device.id}" aria-label="Desvincular el sensor ${escapeHtml(device.name)}">Desvincular</button>
    </div>
  </article>`;
}

function sensorConnectivityCallout(devices, latestByDevice) {
  const entries = devices.map((device) => ({
    device,
    status: deviceStatusInfo(device, latestByDevice.get(device.id)),
  }));
  const live = entries.filter((entry) => entry.status.key === "live");
  const silent = entries.filter((entry) =>
    ["stale", "disconnected", "no_data"].includes(entry.status.key)
  );

  if (!silent.length) return "";

  const liveNames = live.map((entry) => entry.device.name);
  const silentNames = silent.map((entry) => entry.device.name);
  if (liveNames.length) {
    return callout(
      "warning",
      "!",
      "Un sensor dejó de actualizarse",
      `<p>${escapeHtml(liveNames.join(", "))} ${plural(liveNames.length, "sigue", "siguen")} enviando datos. De ${escapeHtml(silentNames.join(", "))} no estamos recibiendo datos nuevos.</p><p>Se muestran los últimos valores recibidos de ${escapeHtml(silentNames.length === 1 ? "ese sensor" : "esos sensores")}, identificados con la fecha y hora de su última recepción.</p>`
    );
  }
  return callout(
    "warning",
    "!",
    "No estamos recibiendo datos nuevos",
    `<p>Revisa que ${escapeHtml(silentNames.join(", "))} ${plural(silentNames.length, "esté encendido y conectado", "estén encendidos y conectados")} a la red y al servidor.</p><p>Si hay lecturas anteriores, se conservan como últimos datos recibidos.</p>`
  );
}

function historyToolbar() {
  const options = [10, 30, 60, 100]
    .map(
      (limit) =>
        `<option value="${limit}"${dashState.historyLimit === limit ? " selected" : ""}>${limit}</option>`
    )
    .join("");
  return `<div class="history-toolbar">
    <div>
      <label for="history-limit">Lecturas en el historial</label>
      <span>La gráfica y la tabla usan este mismo rango.</span>
    </div>
    <select id="history-limit" data-history-limit>${options}</select>
  </div>`;
}

const CHART_METRICS = {
  spo2: {
    label: "Oxígeno en la sangre",
    shortLabel: "SpO₂",
    unit: "%",
    color: "#0f766e",
    reference: [95, 100],
    decimals: 0,
    padding: 2,
    min: 0,
    max: 100,
  },
  pulse: {
    label: "Pulso",
    shortLabel: "Pulso",
    unit: "lpm",
    color: "#b42318",
    reference: [60, 100],
    decimals: 0,
    padding: 8,
    min: 0,
    max: null,
  },
  temp: {
    label: "Temperatura corporal",
    shortLabel: "Temperatura",
    unit: "°C",
    color: "#b45309",
    reference: [36, 37.5],
    decimals: 1,
    padding: 0.8,
    min: 30,
    max: null,
  },
};

let chartSequence = 0;

function chartMetricValue(row, metric) {
  if (metric === "spo2") return numberOrNull(row.spo2);
  if (metric === "pulse") return numberOrNull(row.heart_rate_bpm);
  return numberOrNull(row.temperature_c);
}

function chartRows(readings, metric) {
  return (readings ?? [])
    .filter((row) => {
      if (metric === "temp") {
        return (row.temperature_source ?? tempSource(row.source)) !== "sensor_die";
      }
      return true;
    })
    .map((row) => ({
      value: chartMetricValue(row, metric),
      date: parseDate(row.measured_at),
      device: row.device?.name ?? null,
      source: row.source ?? null,
    }))
    .filter((point) => point.value !== null && point.date)
    .sort((a, b) => a.date.getTime() - b.date.getTime());
}

function chartDomain(points, config) {
  const values = points.map((point) => point.value).concat(config.reference);
  let low = Math.min(...values) - config.padding;
  let high = Math.max(...values) + config.padding;
  if (config.min !== null) low = Math.max(config.min, low);
  if (config.max !== null) high = Math.min(config.max, high);
  if (high - low < config.padding * 2) {
    high += config.padding;
    low -= config.padding;
  }
  return { low, high };
}

function axisValue(value, decimals) {
  return value.toFixed(decimals);
}

function chartTimeLabel(date, firstDate, lastDate, shortSpan) {
  const sameDay =
    firstDate.toDateString() === lastDate.toDateString() &&
    date.toDateString() === firstDate.toDateString();
  if (sameDay && shortSpan) {
    return date.toLocaleTimeString("es", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }
  if (sameDay) return formatTime(date);
  return date.toLocaleString("es", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function svgChartCard(readings, metric) {
  const config = CHART_METRICS[metric];
  const points = chartRows(readings, metric);
  const id = ++chartSequence;
  const titleId = `chart-title-${id}`;
  const descriptionId = `chart-desc-${id}`;

  if (!points.length) {
    const omitted =
      metric === "temp"
        ? readings?.length
          ? " Solo hay lecturas de temperatura interna del sensor, que no se comparan con la temperatura corporal."
          : ""
        : "";
    return `<figure class="chart-card" aria-labelledby="${titleId}">
      <figcaption id="${titleId}"><strong>${escapeHtml(config.label)}</strong><span>${escapeHtml(config.unit)}</span></figcaption>
      <div class="chart-empty">
        <p>Sin lecturas de ${escapeHtml(config.shortLabel.toLowerCase())} para graficar.${escapeHtml(omitted)}</p>
      </div>
    </figure>`;
  }

  const width = 640;
  const height = 230;
  const margin = { top: 18, right: 18, bottom: 42, left: 56 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const firstDate = points[0].date;
  const lastDate = points[points.length - 1].date;
  const span = Math.max(1, lastDate.getTime() - firstDate.getTime());
  const shortSpan = span < 15 * 60 * 1000;
  const { low, high } = chartDomain(points, config);
  const x = (date) =>
    margin.left + (lastDate.getTime() === firstDate.getTime() ? plotWidth / 2 : ((date.getTime() - firstDate.getTime()) / span) * plotWidth);
  const y = (value) => margin.top + ((high - value) / (high - low)) * plotHeight;
  const yTicks = Array.from({ length: 5 }, (_, index) => low + ((high - low) * index) / 4).reverse();
  const bandTop = y(Math.min(high, config.reference[1]));
  const bandBottom = y(Math.max(low, config.reference[0]));
  const polyline = points
    .map((point) => `${x(point.date).toFixed(1)},${y(point.value).toFixed(1)}`)
    .join(" ");
  const circles = points
    .map((point) => {
      const title = `${formatDateTime(point.date)} · ${axisValue(point.value, config.decimals)} ${config.unit}${point.device ? ` · ${point.device}` : ""}`;
      return `<circle cx="${x(point.date).toFixed(1)}" cy="${y(point.value).toFixed(1)}" r="4.5" fill="${config.color}" stroke="#ffffff" stroke-width="2"><title>${escapeHtml(title)}</title></circle>`;
    })
    .join("");
  const gridLines = yTicks
    .map((tick) => {
      const ty = y(tick);
      return `<g class="chart-gridline"><line x1="${margin.left}" y1="${ty.toFixed(1)}" x2="${width - margin.right}" y2="${ty.toFixed(1)}"></line><text x="${margin.left - 10}" y="${(ty + 4).toFixed(1)}" text-anchor="end">${axisValue(tick, config.decimals)}</text></g>`;
    })
    .join("");
  const labelIndices = unique([0, Math.floor((points.length - 1) / 2), points.length - 1]);
  const seenTimes = new Set();
  const xLabels = labelIndices
    .map((index) => ({
      index,
      point: points[index],
      text: chartTimeLabel(points[index].date, firstDate, lastDate, shortSpan),
    }))
    .filter((label) => {
      if (seenTimes.has(label.text)) return false;
      seenTimes.add(label.text);
      return true;
    })
    .map(({ index, point, text }) => {
      return `<text x="${x(point.date).toFixed(1)}" y="${height - 14}" text-anchor="${index === 0 ? "start" : index === points.length - 1 ? "end" : "middle"}">${escapeHtml(text)}</text>`;
    })
    .join("");

  const values = points.map((point) => point.value);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const latest = points[points.length - 1];
  const description = `Serie de ${config.label.toLowerCase()} con ${points.length} ${plural(points.length, "lectura", "lecturas")} entre ${formatDateTime(firstDate)} y ${formatDateTime(lastDate)}. Mínimo ${axisValue(minimum, config.decimals)} ${config.unit}, máximo ${axisValue(maximum, config.decimals)} ${config.unit}, último valor ${axisValue(latest.value, config.decimals)} ${config.unit}.`;

  return `<figure class="chart-card" aria-labelledby="${titleId}">
    <figcaption id="${titleId}">
      <span><strong>${escapeHtml(config.label)}</strong><small>${escapeHtml(config.unit)} · banda de referencia ${axisValue(config.reference[0], config.decimals)}–${axisValue(config.reference[1], config.decimals)}</small></span>
      <span class="chart-count">${points.length} ${plural(points.length, "lectura", "lecturas")}</span>
    </figcaption>
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="${titleId}" aria-describedby="${descriptionId}">
      <desc id="${descriptionId}">${escapeHtml(description)}</desc>
      <rect class="chart-band" x="${margin.left}" y="${bandBottom > bandTop ? bandTop : bandBottom}" width="${plotWidth}" height="${Math.abs(bandBottom - bandTop).toFixed(1)}"></rect>
      ${gridLines}
      <line class="chart-axis" x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}"></line>
      <line class="chart-axis" x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}"></line>
      <polyline class="chart-line" points="${polyline}" fill="none" stroke="${config.color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"></polyline>
      ${circles}
      <g class="chart-xlabels">${xLabels}</g>
    </svg>
    <p class="chart-summary">Mínimo ${axisValue(minimum, config.decimals)} ${escapeHtml(config.unit)} · máximo ${axisValue(maximum, config.decimals)} ${escapeHtml(config.unit)} · último ${axisValue(latest.value, config.decimals)} ${escapeHtml(config.unit)} ${escapeHtml(formatRelative(latest.date))}.${latest.device ? ` Sensor: ${escapeHtml(latest.device)}.` : ""}</p>
  </figure>`;
}

function vitalsCharts(readings) {
  if (!readings?.length) return "";
  return `<div class="chart-grid">${["spo2", "pulse"].map((metric) => svgChartCard(readings, metric)).join("")}</div>`;
}

async function openPairDialog() {
  const form = document.querySelector("#pair-form");
  if (!form) return;
  form.reset();
  showFormError("pair-form-error", "");
  const capacity = document.querySelector("#pair-capacity");
  const submit = document.querySelector("#pair-submit");
  capacity.textContent = "Consultando cupos…";
  capacity.classList.remove("is-blocked");
  submit.disabled = true;
  openDialog("#pair-dialog");
  window.setTimeout(() => document.querySelector("#pairing-code").focus(), 30);

  try {
    const { data } = await apiFetch("/api/devices/capacity");
    updatePairCapacity(data);
  } catch (error) {
    console.error("No se pudo consultar la capacidad de dispositivos", error);
    capacity.textContent = "No pudimos consultar los cupos. Aun así, puedes intentar vincular el sensor.";
    submit.disabled = false;
  }
}

function updatePairCapacity(capacity) {
  const hint = document.querySelector("#pair-capacity");
  const submit = document.querySelector("#pair-submit");
  if (!hint || !submit) return;

  const maxDevices = Number(capacity.max_devices) || 0;
  const available = Number(capacity.available_slots) || 0;
  const perUser = Number(capacity.max_devices_per_user) || 0;
  const userDevices = Number(capacity.user_devices) || 0;

  if (perUser > 0 && userDevices >= perUser) {
    hint.textContent = `Tu cuenta ya tiene el máximo de ${perUser} ${plural(perUser, "sensor", "sensores")}. Desvincula uno antes de conectar otro.`;
    hint.classList.add("is-blocked");
    submit.disabled = true;
    return;
  }
  if (available <= 0) {
    hint.textContent = `El servidor alcanzó el máximo de ${maxDevices} ${plural(maxDevices, "sensor registrado", "sensores registrados")}. Pide al administrador que libere un cupo.`;
    hint.classList.add("is-blocked");
    submit.disabled = true;
    return;
  }

  hint.textContent = `Cupos disponibles: ${available} de ${maxDevices}. Sensores en tu cuenta: ${userDevices} de ${perUser}.`;
  hint.classList.remove("is-blocked");
  submit.disabled = false;
}

function pairErrorMessage(error) {
  if (error?.status === 400) {
    return error.message || "El código no es válido o ya venció. Genera uno nuevo en el monitor serial.";
  }
  if (error?.status === 403) {
    return error.message || "El sensor está desactivado. Pide ayuda al administrador.";
  }
  if (error?.status === 409) {
    return "Ese sensor ya está vinculado a otra cuenta.";
  }
  if (error?.status === 422) {
    return "El código debe tener exactamente 6 dígitos.";
  }
  if (error?.status === 429) {
    return error.message || "Demasiados intentos. Espera un minuto y vuelve a probar.";
  }
  return friendlyError(error, "No pudimos vincular el sensor. Revisa el código e inténtalo de nuevo.");
}

async function submitPairForm(event) {
  event.preventDefault();
  const input = document.querySelector("#pairing-code");
  const code = input.value.replace(/\D/g, "");
  if (code.length !== 6) {
    showFormError("pair-form-error", "Escribe el código de 6 dígitos que muestra el monitor serial.");
    input.focus();
    return;
  }

  input.value = code;
  const button = document.querySelector("#pair-submit");
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Vinculando…";
  showFormError("pair-form-error", "");

  try {
    const { data } = await apiFetch("/api/devices/pair", {
      method: "POST",
      body: JSON.stringify({ pairing_code: code }),
    });
    closeDialog("#pair-dialog");
    showToast(`Sensor vinculado: ${data.name}.`);
    await loadRoleDashboard();
  } catch (error) {
    showFormError("pair-form-error", pairErrorMessage(error));
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

async function unpairDevice(deviceId) {
  const device = dashState.devices.find((item) => item.id === Number(deviceId));
  if (!device) {
    showToast("No encontramos ese sensor. Actualiza la página e inténtalo de nuevo.", "error");
    return;
  }

  const accepted = await askConfirm({
    title: "Desvincular sensor",
    message: `El sensor «${device.name}» dejará de estar vinculado a tu cuenta y no recibirá lecturas nuevas. Las lecturas anteriores se conservan. Para volver a usarlo, borra el archivo device_config.json del ESP32, reinícialo y copia el código nuevo del monitor serial.`,
    confirmLabel: "Sí, desvincular",
    danger: true,
  });
  if (!accepted) return;

  try {
    await apiFetch(`/api/devices/${device.id}/unpair`, { method: "POST" });
    showToast("Sensor desvinculado. Las lecturas anteriores se conservan.");
    await loadRoleDashboard();
  } catch (error) {
    showToast(friendlyError(error, "No pudimos desvincular el sensor."), "error");
  }
}

async function loadPatientDashboard() {
  const { data: devices } = await apiFetch("/api/devices");
  dashState.devices = Array.isArray(devices) ? devices : [];
  const deviceResults = await Promise.all(
    devices.map(async (device) => {
      try {
        const [latestResponse, measurementsResponse] = await Promise.all([
          apiFetch(`/api/devices/${device.id}/latest-measurement`),
          apiFetch(`/api/devices/${device.id}/measurements?limit=${dashState.historyLimit}`),
        ]);
        return {
          device,
          latest: latestResponse.data?.spo2 !== null && latestResponse.data?.spo2 !== undefined ? latestResponse.data : null,
          measurements: measurementsResponse.data ?? [],
        };
      } catch (error) {
        console.error(`No se pudo cargar el sensor ${device.id}`, error);
        return { device, latest: null, measurements: [], error: true };
      }
    })
  );

  const readings = deviceResults
    .flatMap((item) => item.measurements.map((measurement) => ({ ...measurement, device: item.device })))
    .sort((a, b) => dateValue(b.measured_at) - dateValue(a.measured_at));

  const latestItems = deviceResults
    .filter((item) => item.latest)
    .map((item) => ({ device: item.device, latest: item.latest }));

  dashState.sources = unique([
    ...readings.map((measurement) => measurement.source),
    ...latestItems.map((item) => item.latest.source),
  ]);

  renderPatientDashboard({ devices, readings, latestItems });
}

function patientOverallStatus(latestItems, primary) {
  const recent = latestItems.filter((item) => isWithin(item.latest.taken_at, ATTENTION_WINDOW));
  let worst = "normal";
  recent.forEach((item) => {
    worst = worseStatus(worst, combinedStatusFromVitals(item.latest));
  });
  if (worst === "review" || worst === "critical") return worst;
  if (primary && isWithin(primary.measured_at, RECENT_WINDOW)) return "normal";
  if (primary) return "offline";
  return "no_data";
}

function patientCallout(status, alerts, primary) {
  const when = primary ? formatRelative(primary.measured_at) : "";
  const where = primary?.device?.name ? ` · ${primary.device.name}` : "";

  if (status === "critical") {
    return callout(
      "danger",
      "!",
      "Hay valores que necesitan atención",
      `<p>Revisa las lecturas y cómo te sientes.</p>${alertListHtml(alerts)}<p>Si tienes dificultad para respirar, dolor en el pecho o te sientes muy mal, busca atención médica ahora.</p>`
    );
  }
  if (status === "review") {
    return callout(
      "warning",
      "!",
      "Hay valores para revisar",
      `<p>Una o más lecturas están un poco fuera de los valores de referencia.</p>${alertListHtml(alerts)}<p>No es un diagnóstico. Observa cómo te sientes y vuelve a medir después de descansar.</p>`
    );
  }
  if (status === "offline") {
    return callout(
      "info",
      "i",
      "La última lectura es de hace un tiempo",
      `<p>Última lectura: ${escapeHtml(when)}${escapeHtml(where)}.</p><p>Revisa que el sensor esté encendido y conectado. También puedes usar «Actualizar».</p>`
    );
  }
  if (status === "no_data") {
    return callout(
      "info",
      "i",
      "Todavía no hay lecturas",
      "<p>Cuando tu sensor envíe la primera lectura, la verás aquí. Revisa que esté encendido y conectado.</p>"
    );
  }
  return callout(
    "success",
    "✓",
    "Tus últimas lecturas están en rango",
    `<p>Última lectura: ${escapeHtml(when)}${escapeHtml(where)}.</p><p>Estos valores son de referencia. Si te sientes mal, busca atención aunque la app muestre valores en rango.</p>`
  );
}

function renderPatientDashboard({ devices, readings, latestItems }) {
  const content = document.querySelector("#dash-content");
  const primary = readings[0] ?? null;
  const status = patientOverallStatus(latestItems, primary);
  const alerts = unique(
    latestItems
      .filter((item) => isWithin(item.latest.taken_at, ATTENTION_WINDOW))
      .flatMap((item) => alertsFor(item.latest).map((alert) => `${item.device.name}: ${alert}`))
  );

  const latestByDevice = new Map(latestItems.map((item) => [item.device.id, item.latest]));
  const primaryVitals = primary ? { ...primary } : null;
  const meta = primaryVitals
    ? `Última: ${formatRelative(primaryVitals.measured_at)} · ${primaryVitals.device.name}`
    : "Sin lecturas todavía";

  const sensors = devices.map((device) => sensorCard({ device }, latestByDevice.get(device.id))).join("");
  const history = readings.slice(0, dashState.historyLimit);
  const readingsHtml = measurementsTable(history, {
    caption: `Historial de ${history.length} ${plural(history.length, "lectura", "lecturas")} de tus sensores.`,
  });

  content.innerHTML = `
    <section class="dash-section" id="resumen" data-dash-section>
      ${patientCallout(status, alerts, primary)}
      <div class="vital-grid section-gap-top">
        ${vitalCard({
          label: "Oxígeno en la sangre",
          value: primaryVitals?.spo2 ?? null,
          unit: "%",
          status: primaryVitals ? metricStatus("spo2", primaryVitals.spo2) : "no_data",
          meta,
          reference: "Referencia: 95–100%",
          icon: "drop",
        })}
        ${vitalCard({
          label: "Pulso",
          value: primaryVitals?.heart_rate_bpm ?? null,
          unit: "lpm",
          status: primaryVitals ? metricStatus("pulse", primaryVitals.heart_rate_bpm) : "no_data",
          meta,
          reference: "Referencia: 60–100 lpm",
          icon: "heart",
        })}
      </div>
    </section>

    <section class="dash-section" id="apnea" data-dash-section>
      ${sectionHead("APNEA", "Cronómetro tranquilo", "Acompaña tu intento de apnea. Respira con calma; el color cambia suavemente según tu oxígeno actual.")}
      <div class="apnea-timer-card">
        <div id="apnea-semaphore" class="apnea-semaphore is-green" role="status" aria-live="polite">
          <span class="semaphore-dot" aria-hidden="true"></span>
          <span id="apnea-semaphore-text">Oxígeno en rango</span>
        </div>
        <div id="apnea-timer-display" class="apnea-timer" aria-live="off">00:00</div>
        <div class="apnea-timer-actions">
          <button type="button" class="dash-button" id="apnea-start">Iniciar</button>
          <button type="button" class="dash-button dash-button-quiet" id="apnea-pause">Pausar</button>
          <button type="button" class="dash-button dash-button-quiet" id="apnea-reset">Reiniciar</button>
        </div>
        <p class="dash-muted">Sin alertas sonoras. El semáforo se actualiza con tu última lectura.</p>
      </div>
    </section>

    <section class="dash-section" id="lecturas" data-dash-section>
      ${sectionHead("LECTURAS", "Historial y tendencia", "Cada punto de la gráfica corresponde a una lectura recibida. La banda sombreada marca el rango de referencia.")}
      ${historyToolbar()}
      ${vitalsCharts(history)}
      ${readingsHtml}
      ${sourceNote(dashState.sources)}
      <p class="reference-note">Valores de referencia: oxígeno 95–100% · pulso 60–100 lpm. No son un diagnóstico.</p>
    </section>

    <section class="dash-section" id="sensores" data-dash-section>
      ${sectionHead("SENSORES", "Tus sensores", "Dispositivos vinculados a tu cuenta. Cada tarjeta muestra su último contacto, su última lectura y el origen del dato.")}
      ${devices.length ? `<div class="sensor-grid">${sensors}</div>` : emptyState({
        title: "Aún no tienes sensores",
        text: "Enciende tu ESP32, copia el código de 6 dígitos del monitor serial e ingrésalo aquí para vincularlo a tu cuenta.",
        actionLabel: "Conectar mi sensor",
        actionAttr: "data-open-pair",
        icon: "device",
      })}
    </section>

    <section class="dash-section" id="recomendaciones" data-dash-section>
      ${sectionHead("QUÉ PUEDES HACER", "Recomendaciones de cuidado", "Consejos generales. No sustituyen la indicación de tu profesional de la salud.")}
      <div class="grid-2">
        <article class="dash-card">
          <h3>Cuando hay una alerta</h3>
          <ul class="plain-list">
            <li>Anota cómo te sientes y si tienes síntomas.</li>
            <li>Vuelve a medir después de descansar 5 minutos.</li>
            <li>Si empeoras o tienes dificultad para respirar, busca atención médica.</li>
            <li>No cambies medicamentos ni dosis por tu cuenta.</li>
          </ul>
        </article>
        <article class="dash-card">
          <h3>Para medir mejor</h3>
          <ul class="plain-list">
            <li>Siéntate y descansa antes de medir.</li>
            <li>Coloca el sensor como te indicó el equipo de salud.</li>
            <li>Revisa que el sensor esté encendido y conectado.</li>
            <li>Una sola lectura no reemplaza una valoración profesional.</li>
          </ul>
        </article>
      </div>
    </section>

    <section class="dash-section" id="records" data-dash-section>
      ${sectionHead("RÉCORDS PERSONALES", "Tu progreso en apnea y deportes", "Máxima retención, mejor oxigenación y frecuencia en reposo, comparado con tu historial.")}
      ${(function () {
        const pbs = computePBs(readings, devices);
        const maxHR = estimateMaxHR();
        const hrZoneInfo = pbs.avgRestingPulse ? hrZone(maxHR, pbs.avgRestingPulse) : null;
        return `
        <div class="pb-grid">
          <article class="pb-card pb-breath">
            <p class="pb-eyebrow">Apnea estática</p>
            <p class="pb-value">${pbs.maxBreathHold}<small>s</small></p>
            <p class="pb-delta is-up">Tu récord personal</p>
            <p class="pb-note">Tiempo máximo de retención de aire.</p>
          </article>
          <article class="pb-card pb-oxygen">
            <p class="pb-eyebrow">Mejor SpO₂</p>
            <p class="pb-value">${pbs.bestSpO2 ?? "—"}<small>%</small></p>
            <p class="pb-delta ${pbs.bestSpO2 && pbs.bestSpO2 >= 95 ? "is-up" : "is-down"}${pbs.bestSpO2 && pbs.bestSpO2 >= 95 ? "En rango óptimo" : "Por debajo de lo óptimo"}</p>
            <p class="pb-note">Mejor oxigenación registrada.</p>
          </article>
          <article class="pb-card pb-heart">
            <p class="pb-eyebrow">Pulso en reposo</p>
            <p class="pb-value">${pbs.avgRestingPulse ?? "—"}<small>lpm</small></p>
            <p class="pb-delta is-up">${hrZoneInfo ? `Zona ${hrZoneInfo.z} · ${hrZoneInfo.name}` : "—"}</p>
            <p class="pb-note">Frecuencia cardíaca basal estimada.</p>
          </article>
          <article class="pb-card pb-sessions">
            <p class="pb-eyebrow">Sesiones</p>
            <p class="pb-value">${pbs.sessions}<small></small></p>
            <p class="pb-delta is-up">Días con lecturas</p>
            <p class="pb-note">Últimos 30 días de historial.</p>
          </article>
        </div>
        `;
      })()}
    </section>

    <section class="dash-section" id="calendario" data-dash-section>
      ${sectionHead("CALENDARIO DE ACTIVIDAD", "Últimos 30 días", "Días con al menos una lectura. Más oscuro = más actividad (estilo Strava).")}
      <div class="activity-calendar">
        <div class="ac-header">
          <span class="ac-title">Actividad reciente</span>
          <div class="ac-legend">
            <span class="ac-legend-dot is-4"></span><span>Mucho</span>
            <span class="ac-legend-dot is-1"></span><span>Poco</span>
          </div>
        </div>
        <div class="ac-weekday">
          <span>Lu</span><span>Ma</span><span>Mi</span><span>Ju</span><span>Vi</span><span>Sá</span><span>Do</span>
        </div>
        <div class="ac-grid">
          ${activityCalendarDays(readings).map((day) => `<div class="ac-cell is-${day.level}" title="${day.key}: ${day.count} lectura${day.count !== 1 ? "s" : ""}"></div>`).join("")}
        </div>
      </div>
    </section>

    <section class="dash-section" id="tablas-entrenamiento" data-dash-section>
      ${sectionHead("TABLAS DE ENTRENAMIENTO", "CO₂ y O₂ personalizadas", "Generadas a partir de tu retención máxima. Estilo Fathom / Apnea Assistant.")}
      <div class="training-tables">
        <article class="training-table-card tt-co2">
          <p class="tt-eyebrow">Tolerancia al CO₂</p>
          <h3>Tabla CO₂</h3>
          <p>Retenciones fijas con descansos cada vez más cortos. Entrena tu tolerancia al deseo de respirar.</p>
          <div class="tt-stats">
            <div class="tt-stat"><div class="tt-stat-value">${co2Table(90).hold}s</div><div class="tt-stat-label">Retención</div></div>
            <div class="tt-stat"><div class="tt-stat-value">8</div><div class="tt-stat-label">Rondas</div></div>
          </div>
          <div class="tt-actions">
            <button type="button" class="tt-btn" style="background: var(--dash-red); color: var(--white);">Iniciar tabla CO₂</button>
          </div>
        </article>
        <article class="training-table-card tt-o2">
          <p class="tt-eyebrow">Resistencia al O₂</p>
          <h3>Tabla O₂</h3>
          <p>Retenciones progresivas con descanso fijo. Entrena tu cuerpo a trabajar con menos oxígeno.</p>
          <div class="tt-stats">
            <div class="tt-stat"><div class="tt-stat-value">~75%</div><div class="tt-stat-label">De tu máximo</div></div>
            <div class="tt-stat"><div class="tt-stat-value">8</div><div class="tt-stat-label">Rondas</div></div>
          </div>
          <div class="tt-actions">
            <button type="button" class="tt-btn" style="background: var(--dash-cyan); color: var(--black);">Iniciar tabla O₂</button>
          </div>
        </article>
      </div>
    </section>

    <section class="dash-section" id="respiracion" data-dash-section>
      ${sectionHead("RESPIRACIÓN GUIADA", "Box breathing · 4-7-8 · Diafragmática", "Ejercicios de respiración para pre-inmersión y recuperación de superficie.")}
      <div class="breathing-guide">
        <div class="breathing-circle">
          <div class="breathing-ring"></div>
        </div>
        <div class="breathing-text">Inhalar <span>4s</span></div>
        <div class="breathing-phase" id="breath-phase">Preparado</div>
        <div class="breathing-actions">
          <button type="button" class="tt-btn" style="background: var(--dash-cyan); color: var(--black);" id="breath-start">Iniciar</button>
          <button type="button" class="tt-btn" id="breath-pause">Pausar</button>
        </div>
      </div>
    </section>

    <section class="dash-section" id="zonas-fc" data-dash-section>
      ${sectionHead("ZONAS DE FRECUENCIA CARDÍACA", "Entrena por intensidad", "Cinco zonas basadas en tu FC máxima estimada (220 − edad). Estilo MySwimPro / SwimTune.")}
      <div class="hr-zones">
        ${[1, 2, 3, 4, 5].map((z) => {
          const maxHR = estimateMaxHR();
          const lo = Math.round(maxHR * (z === 1 ? 0 : [0, 0.6, 0.7, 0.8, 0.9][z - 1]));
          const hi = Math.round(maxHR * [0.6, 0.7, 0.8, 0.9, 1][z - 1]);
          const time = z === 3 ? "42%" : z === 2 ? "28%" : z === 4 ? "18%" : z === 5 ? "8%" : "26%";
          const colors = ["#0f766e", "#d97706", "#00b4d8", "#b91c1c", "#78288c"];
          return `<article class="hr-zone is-z${z}">
            <span class="hz-dot" style="background: ${colors[z - 1]};"></span>
            <div class="hz-name">Zona ${z}</div>
            <div class="hz-range">${lo}–${hi} lpm</div>
            <div class="hz-time">${time}</div>
          </article>`;
        }).join("")}
      </div>
    </section>

    <section class="dash-section" id="carga-entrenamiento" data-dash-section>
      ${sectionHead("CARGA DE ENTRENAMIENTO", "Aguda (7d) vs Crónica (28d)", "Equilibrio entre carga reciente y carga acumulada. Estilo Swim Dashboard.")}
      ${(function () {
        const tl = trainingLoad(readings);
        const ratio = tl.chronic ? Math.round((tl.acute / tl.chronic) * 100) : 0;
        return `
        <div class="training-load">
          <article class="tl-card is-acute">
            <p class="tl-eyebrow">Carga aguda</p>
            <div class="tl-value">${tl.acute}</div>
            <div class="tl-label">Lecturas últimos 7 días</div>
          </article>
          <article class="tl-card is-chronic">
            <p class="tl-eyebrow">Carga crónica</p>
            <div class="tl-value">${tl.chronic}</div>
            <div class="tl-label">Lecturas últimos 28 días</div>
          </article>
          <article class="tl-card" style="border-left-color: var(--dash-amber);">
            <p class="tl-eyebrow">Racha actual</p>
            <div class="tl-value">${computeStreak(activityCalendarDays(readings))}<small>días</small></div>
            <div class="tl-label">Días seguidos entrenando</div>
          </article>
        </div>
        <p class="reference-note">${ratio > 150 ? "Carga aguda elevada respecto a la crónica. Considera un día de recuperación." : ratio < 80 && tl.chronic > 0 ? "Puedes aumentar gradualmente la carga de entrenamiento." : "Carga equilibrada. Mantén la consistencia."}</p>
        `;
      })()}
    </section>`;
  updateApneaSemaphore(primaryVitals?.spo2 ?? null);
}

// ============================================================================
// MEJORAS COMPETENCIA: APNEA / DEPORTES
// Récords personales, calendario de actividad, tablas CO₂/O₂, respiración guiada,
// zonas de FC, carga de entrenamiento y racha. Datos derivados de lecturas.
// ============================================================================

function estimateMaxHR(age = 35) {
  return Math.max(30, 220 - age);
}

function hrZone(maxHR, bpm) {
  const pct = bpm / maxHR;
  if (pct < 0.60) return { z: 1, name: "Recuperación", color: "#0f766e" };
  if (pct < 0.70) return { z: 2, name: "Resistencia", color: "#d97706" };
  if (pct < 0.80) return { z: 3, name: "Aeróbica", color: "#00b4d8" };
  if (pct < 0.90) return { z: 4, name: "Umbral", color: "#b91c1c" };
  return { z: 5, name: "VO2máx", color: "#78288c" };
}

function computePBs(readings, devices) {
  const spo2Values = readings
    .map((r) => Number(r.spo2))
    .filter((v) => Number.isFinite(v) && v > 0);
  const pulseValues = readings
    .map((r) => Number(r.heart_rate_bpm))
    .filter((v) => Number.isFinite(v) && v > 0);
  const bestSpO2 = spo2Values.length ? Math.max(...spo2Values) : null;
  const worstSpO2 = spo2Values.length ? Math.min(...spo2Values) : null;
  const avgRestingPulse = pulseValues.length
    ? Math.round(pulseValues.filter((v) => v < 90).reduce((a, b) => a + b, 0) / pulseValues.filter((v) => v < 90).length)
    : null;
  const maxBreathHold = 90; // simulado: segundos (en futuro vendría del sensor/apnea timer)
  const sessions = unique(readings.map((r) => r.measured_at?.slice(0, 10))).length;
  return { bestSpO2, worstSpO2, avgRestingPulse, maxBreathHold, sessions };
}

function activityCalendarDays(readings) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    days.push(d);
  }
  const counts = {};
  readings.forEach((r) => {
    if (!r.measured_at) return;
    const ds = r.measured_at.slice(0, 10);
    counts[ds] = (counts[ds] || 0) + 1;
  });
  return days.map((d) => {
    const key = d.toISOString().slice(0, 10);
    const c = counts[key] || 0;
    let level = 0;
    if (c >= 5) level = 4;
    else if (c >= 3) level = 3;
    else if (c === 2) level = 2;
    else if (c === 1) level = 1;
    return { date: d, key, count: c, level };
  });
}

function computeStreak(calendarDays) {
  let streak = 0;
  for (let i = calendarDays.length - 1; i >= 0; i--) {
    if (calendarDays[i].count > 0) streak++;
    else break;
  }
  return streak;
}

function trainingLoad(readings) {
  const now = Date.now();
  const acuteMs = 7 * 24 * 60 * 60 * 1000;
  const chronicMs = 28 * 24 * 60 * 60 * 1000;
  const acute = readings.filter((r) => now - dateValue(r.measured_at) <= acuteMs).length;
  const chronic = readings.filter((r) => now - dateValue(r.measured_at) <= chronicMs).length;
  return { acute, chronic };
}

function co2Table(maxHoldSeconds) {
  const rounds = 8;
  const hold = Math.max(10, Math.round(maxHoldSeconds * 0.5));
  const rows = [];
  let rest = 90;
  for (let i = 0; i < rounds; i++) {
    rows.push({ round: i + 1, hold, rest });
    rest = Math.max(30, rest - 10);
  }
  return { hold, rest, rows };
}

function o2Table(maxHoldSeconds) {
  const rounds = 8;
  const base = Math.max(10, Math.round(maxHoldSeconds * 0.75));
  const rows = [];
  const rest = 120;
  for (let i = 0; i < rounds; i++) {
    rows.push({ round: i + 1, hold: base + i * 5, rest });
  }
  return { base, rest, rows };
}

function breathingCycles(type = "box") {
  if (type === "box") return [{ name: "Inhalar", s: 4 }, { name: "Mantener", s: 4 }, { name: "Exhalar", s: 4 }, { name: "Mantener", s: 4 }];
  if (type === "4-7-8") return [{ name: "Inhalar", s: 4 }, { name: "Mantener", s: 7 }, { name: "Exhalar", s: 8 }];
  if (type === "diafragmatica") return [{ name: "Inhalar", s: 5 }, { name: "Exhalar", s: 6 }];
  return [{ name: "Inhalar", s: 4 }, { name: "Exhalar", s: 4 }];
}

async function loadCareDashboard(role) {
  const { data: patients } = await apiFetch("/api/care/patients");
  dashState.carePatients = patients;
  renderCareDashboard(role, patients);
}

function careCallout(patient) {
  const name = patient.patient.full_name;
  const first = firstName(name);
  const when = patient.latest ? formatRelative(patient.latest.taken_at) : "";
  const alerts = patient.alerts ?? [];

  if (patient.status === "critical") {
    return callout(
      "danger",
      "!",
      `Revisa a ${first}`,
      `<p>Hay lecturas que necesitan atención.</p>${alertListHtml(alerts)}<p>Si la persona tiene dificultad para respirar, dolor en el pecho o está muy decaída, busca atención médica ahora.</p>`
    );
  }
  if (patient.status === "review") {
    return callout(
      "warning",
      "!",
      `Revisa a ${first}`,
      `<p>Hay lecturas un poco fuera de los valores de referencia.</p>${alertListHtml(alerts)}<p>Una alerta no es un diagnóstico. Contacta a la persona y observa cómo se siente.</p>`
    );
  }
  if (patient.status === "offline") {
    return callout(
      "info",
      "i",
      `No hay una lectura reciente de ${first}`,
      `<p>Última lectura: ${escapeHtml(when)}.</p><p>Revisa que el sensor esté encendido y conectado. Si necesitas actualizar, usa el botón «Actualizar».</p>`
    );
  }
  if (patient.status === "no_data") {
    return callout(
      "info",
      "i",
      `Todavía no hay lecturas de ${first}`,
      "<p>Cuando el sensor envíe la primera lectura, la verás aquí. Revisa que esté encendido y conectado.</p>"
    );
  }
  return callout(
    "success",
    "✓",
    `Las lecturas de ${first} están en rango`,
    `<p>Última lectura: ${escapeHtml(when)}.</p><p>Si la persona se siente mal, busca atención aunque la app muestre valores en rango.</p>`
  );
}

function carePatientCard(patient) {
  const latest = patient.latest;
  const alerts = patient.alerts ?? [];
  const name = patient.patient.full_name;
  const relation = patient.relationship === "caregiver" ? "A tu cuidado" : "Deportista asignado";
  const lastLine = latest
    ? `Última lectura: ${formatRelative(latest.taken_at)} · ${patient.device_count} ${plural(patient.device_count, "sensor", "sensores")} · ${sourceLabel(latest.source)}`
    : `Sin lecturas · ${patient.device_count} ${plural(patient.device_count, "sensor", "sensores")}`;
  const alertBox = alerts.length
    ? `<div class="patient-alerts ${patient.status === "critical" ? "is-critical" : ""}"><strong>Para revisar</strong>${alertListHtml(alerts.slice(0, 3))}</div>`
    : "";

  return `<article class="dash-card patient-card">
    <div class="patient-head">
      <div>
        <h3>${escapeHtml(name)}</h3>
        <p class="patient-relation">${escapeHtml(relation)}</p>
      </div>
      ${statusPill(patient.status)}
    </div>
    ${miniVitals(latest)}
    <p class="dash-muted">${escapeHtml(lastLine)}</p>
    ${alertBox}
    <button type="button" class="dash-button dash-button-quiet" data-patient-id="${patient.patient.id}" aria-label="Ver detalle de ${escapeHtml(name)}">Ver detalle</button>
  </article>`;
}

function renderCareDashboard(role, patients) {
  const content = document.querySelector("#dash-content");
  const specialist = role === "specialist";
  const attention = patients.filter((patient) => patient.status === "review" || patient.status === "critical");
  const critical = patients.filter((patient) => patient.status === "critical");
  const withoutData = patients.filter((patient) => patient.status === "offline" || patient.status === "no_data");
  const deviceCount = patients.reduce((total, patient) => total + patient.device_count, 0);
  const names = attention.map((patient) => firstName(patient.patient.full_name));
  const careSources = unique(patients.map((patient) => patient.latest?.source).filter(Boolean));

  let summary;
  if (critical.length) {
    summary = callout(
      "danger",
      "!",
      "Hay deportistas que necesitan atención",
      `<p>${escapeHtml(names.join(", "))} ${plural(names.length, "tiene", "tienen")} lecturas que necesitan atención.</p><p>Revisa el detalle y contacta según tu protocolo.</p>`
    );
  } else if (attention.length) {
    summary = callout(
      "warning",
      "!",
      "Hay deportistas para revisar",
      `<p>${escapeHtml(names.join(", "))} ${plural(names.length, "tiene", "tienen")} lecturas un poco fuera de los valores de referencia.</p><p>Una alerta no es un diagnóstico. Revisa cómo se siente la persona.</p>`
    );
  } else if (patients.length) {
    summary = callout(
      "success",
      "✓",
      "No hay alertas recientes",
      "<p>Las lecturas de tus deportistas están en rango o no tienen datos nuevos. Puedes revisar el detalle cuando quieras.</p>"
    );
  } else {
    summary = callout(
      "info",
      "i",
      "Todavía no tienes deportistas asignados",
      "<p>Pide al administrador que cree un vínculo de cuidado. En esta versión no se crean cuentas nuevas.</p>"
    );
  }

  content.innerHTML = `
    <section class="dash-section" id="resumen" data-dash-section>
      ${sectionHead(
        specialist ? "RESUMEN CLÍNICO" : "RESUMEN DE ACOMPAÑAMIENTO",
        specialist ? "Tus deportistas asignados" : "Las personas a tu cuidado",
        specialist
          ? "Revisa las últimas lecturas y los sensores de tus deportistas."
          : "Revisa cómo están las personas que tienes asignadas."
      )}
      <div class="grid-4 section-gap-bottom">
        ${metricCard("Personas asignadas", String(patients.length), patients.length === 1 ? "Un deportista" : "Deportistas")}
        ${metricCard("Para revisar", String(attention.length), attention.length === 1 ? "Una persona" : "Personas")}
        ${metricCard("Sensores", String(deviceCount), deviceCount === 1 ? "Un sensor" : "Sensores")}
        ${metricCard("Sin lectura reciente", String(withoutData.length), withoutData.length === 1 ? "Una persona" : "Personas")}
      </div>
      ${summary}
    </section>

    <section class="dash-section" id="deportistas" data-dash-section>
      ${sectionHead(
        "PACIENTES",
        specialist ? "Deportistas para revisar" : "Mis deportistas",
        "Abre el detalle para ver los signos vitales, los sensores y las lecturas recientes."
      )}
      ${patients.length ? `<div class="patient-grid">${patients.map(carePatientCard).join("")}</div>` : emptyState({
        title: "Aún no tienes personas asignadas",
        text: "El administrador debe crear un vínculo entre tu cuenta y un deportista. Mientras tanto, puedes consultar la guía de ayuda.",
        actionLabel: "Ver ayuda",
        actionAttr: "data-open-help",
        icon: "users",
      })}
      <p class="reference-note">Las lecturas son de apoyo y no sustituyen una valoración profesional.</p>
      ${sourceNote(careSources)}
    </section>

    <section class="dash-section" id="recomendaciones" data-dash-section>
      ${sectionHead(
        "CÓMO ACOMPAÑAR",
        specialist ? "Cómo revisar las lecturas" : "Cómo acompañar",
        specialist
          ? "Recomendaciones generales para revisar la información de tus deportistas."
          : "Recomendaciones generales para acompañar sin reemplazar la atención profesional."
      )}
      <div class="grid-2">
        <article class="dash-card">
          <h3>${specialist ? "Al revisar una alerta" : "Cuando hay una alerta"}</h3>
          <ul class="plain-list">
            <li>${specialist ? "Revisa la tendencia, no solo una lectura aislada." : "Llama a la persona y pregunta cómo se siente."}</li>
            <li>${specialist ? "Confirma con el deportista cómo se siente y si tiene síntomas." : "No te bases solo en los números: observa si hay síntomas."}</li>
            <li>${specialist ? "Sigue el protocolo de tu institución." : "Si hay dificultad para respirar, dolor en el pecho o desmayo, llama a emergencias."}</li>
            <li>${specialist ? "Las lecturas son de apoyo; no sustituyen tu valoración." : "No cambies medicamentos ni dosis por tu cuenta."}</li>
          </ul>
        </article>
        <article class="dash-card">
          <h3>Para tener en cuenta</h3>
          <ul class="plain-list">
            <li>Los rangos son de referencia y no un diagnóstico.</li>
            <li>Una lectura puede variar por el movimiento, el frío o la colocación del sensor.</li>
            <li>Si no hay datos, revisa que el sensor esté encendido y conectado.</li>
            <li>Ante una emergencia, llama al 911 o al número local de emergencias.</li>
          </ul>
        </article>
      </div>
    </section>`;
}

async function openPatientDetail(patientId) {
  const dialog = document.querySelector("#patient-dialog");
  const body = document.querySelector("#patient-dialog-body");
  dashState.detailPatientId = patientId;
  document.querySelector("#patient-dialog-title").textContent = "Detalle del deportista";
  document.querySelector("#patient-dialog-kicker").textContent = "PACIENTE";
  body.innerHTML = '<p class="dash-muted">Cargando información…</p>';
  openDialog("#patient-dialog");

  try {
    const { data } = await apiFetch(`/api/care/patients/${patientId}?limit=${dashState.historyLimit}`);
    renderPatientDetail(data);
  } catch (error) {
    const message = error.status === 403 ? "No tienes una asignación activa con este deportista." : "Revisa tu conexión y vuelve a intentarlo.";
    body.innerHTML = `<div class="empty-state" role="alert">
      <div class="empty-icon">${iconFor("alert")}</div>
      <h3>No pudimos cargar el detalle</h3>
      <p>${escapeHtml(message)}</p>
      <button type="button" class="dash-button dash-button-primary" data-patient-retry="${patientId}">Volver a intentar</button>
    </div>`;
  }
}

function renderPatientDetail(data) {
  const name = data.patient.full_name;
  document.querySelector("#patient-dialog-title").textContent = name;
  document.querySelector("#patient-dialog-kicker").textContent =
    data.relationship === "caregiver" ? "PERSONA A TU CUIDADO" : "PACIENTE ASIGNADO";

  const body = document.querySelector("#patient-dialog-body");
  const deviceRows = data.devices
    .map(
      (device) => {
        const status = deviceStatusInfo(device);
        return `<tr>
        <td><strong>${escapeHtml(device.name)}</strong><small>${escapeHtml(device.device_id)}</small></td>
        <td>${escapeHtml(device.location || "Sin ubicación")}</td>
        <td>${statusPill(status.key, status.label)}</td>
        <td>${device.last_seen ? escapeHtml(formatRelative(device.last_seen)) : "Sin contacto"}</td>
      </tr>`;
      }
    )
    .join("");

  const deviceTable = data.devices.length
    ? `<div class="table-wrap"><table>
        <caption>Sensores asignados a ${escapeHtml(name)}.</caption>
        <thead><tr><th scope="col">Sensor</th><th scope="col">Ubicación</th><th scope="col">Estado</th><th scope="col">Último contacto</th></tr></thead>
        <tbody>${deviceRows}</tbody>
      </table></div>`
    : emptyState({ title: "Sin sensores", text: "Este deportista no tiene sensores vinculados.", icon: "device" });

  const deviceById = new Map(data.devices.map((device) => [device.id, device]));
  const history = data.measurements
    .map((row) => ({ ...row, device: deviceById.get(row.device_id) }))
    .slice(0, dashState.historyLimit);
  const sources = unique(history.map((row) => row.source));

  const readings = measurementsTable(history, {
    showDevice: true,
    caption: `Historial de ${history.length} ${plural(history.length, "lectura", "lecturas")} de ${name}.`,
  });

  body.innerHTML = `
    ${careCallout(data)}
    <h3>Últimos signos vitales</h3>
    ${miniVitals(data.latest)}
    <p class="reference-note">Referencia: oxígeno 95–100% · pulso 60–100 lpm · temperatura corporal 36.0–37.5 °C.</p>
    <h3>Sensores asignados</h3>
    ${deviceTable}
    <h3>Historial y tendencia</h3>
    ${historyToolbar()}
    ${vitalsCharts(history)}
    ${readings}
    ${sourceNote(sources)}
    <p class="reference-note">Las lecturas no sustituyen una valoración profesional.</p>`;
}


// ============================================================================
// ADMINISTRACIÓN — USUARIOS, SENSORES Y VÍNCULOS DE CUIDADO
// ============================================================================

const RELATIONSHIP_LABELS = {
  caregiver: "Entrenador",
  specialist: "Entrenador",
};

function personOption(person) {
  return `<option value="${person.id}">${escapeHtml(person.full_name)} · ${escapeHtml(roleLabel(person.role))}</option>`;
}

async function loadAdminDashboard() {
  const includeInactive = Boolean(dashState.assignmentsIncludeInactive);
  const [usersResponse, devicesResponse, assignmentsResponse] = await Promise.all([
    apiFetch("/api/users"),
    apiFetch("/api/devices"),
    apiFetch(`/api/care/assignments?include_inactive=${includeInactive}`),
  ]);

  dashState.users = Array.isArray(usersResponse.data) ? usersResponse.data : [];
  dashState.devices = Array.isArray(devicesResponse.data) ? devicesResponse.data : [];
  dashState.assignments = Array.isArray(assignmentsResponse.data) ? assignmentsResponse.data : [];
  renderAdminDashboard();
}

function renderAdminDashboard() {
  const content = document.querySelector("#dash-content");
  const users = dashState.users;
  const devices = dashState.devices;
  const assignments = dashState.assignments;
  const activeUsers = users.filter((user) => user.is_active);
  const patients = activeUsers.filter((user) => user.role === "patient");
  const members = activeUsers.filter((user) => user.role === "caregiver" || user.role === "specialist");
  const activeDevices = devices.filter((device) => device.is_active);
  const inactiveDevices = devices.filter((device) => !device.is_active);
  const activeAssignments = assignments.filter((assignment) => assignment.is_active);

  let summary = callout(
    "info",
    "i",
    "Resumen de administración",
    `<p>Tienes ${users.length} ${plural(users.length, "cuenta registrada", "cuentas registradas")}, ${devices.length} ${plural(devices.length, "sensor", "sensores")} y ${activeAssignments.length} ${plural(activeAssignments.length, "vínculo activo", "vínculos activos")}.</p><p>Desde «Usuarios» puedes dar de alta cuentas con el correo institucional, asignar su contraseña en persona y desactivar accesos.</p>`
  );

  if (!activeAssignments.length) {
    summary = callout(
      "warning",
      "!",
      "Aún no hay vínculos activos",
      "<p>Sin un vínculo, un entrenador o entrenador no puede ver las lecturas de un deportista. Crea el primero en la sección «Vínculos».</p>"
    );
  }

  const deviceWarning = inactiveDevices.length
    ? callout(
        "warning",
        "!",
        "Hay sensores desactivados",
        `<p>${inactiveDevices.length} ${plural(inactiveDevices.length, "sensor no recibe", "sensores no reciben")} lecturas nuevas. Puedes activarlos en la sección «Sensores».</p>`
      )
    : "";

  content.innerHTML = `
    <section class="dash-section" id="resumen" data-dash-section>
      ${sectionHead(
        "ADMINISTRACIÓN",
        "Resumen del sistema",
        "Usuarios, sensores y vínculos de cuidado."
      )}
      <div class="grid-4 section-gap-bottom">
        ${metricCard("Cuentas", String(users.length), `${activeUsers.length} ${plural(activeUsers.length, "activa", "activas")}`)}
        ${metricCard("Deportistas", String(patients.length), "Cuentas con rol de deportista")}
        ${metricCard("Sensores activos", String(activeDevices.length), `${devices.length} en total`)}
        ${metricCard("Vínculos activos", String(activeAssignments.length), "Deportista y acompañante")}
      </div>
      ${summary}
      ${deviceWarning ? `<div class="section-gap-top">${deviceWarning}</div>` : ""}
    </section>

    <section class="dash-section" id="admin-usuarios" data-dash-section>
      ${sectionHead(
        "USUARIOS",
        "Cuentas registradas",
        "Da de alta cuentas nuevas con el correo del estudiante, asigna su contraseña en persona y desactiva accesos."
      )}
      ${adminUserForm()}
      <div class="section-gap-top">
        ${adminUsersTable(users)}
      </div>
    </section>

    <section class="dash-section" id="admin-sensores" data-dash-section>
      ${sectionHead(
        "SENSORES",
        "Dispositivos registrados",
        "Edita el nombre, la ubicación o el estado de un sensor. Desactivarlo no borra sus lecturas anteriores."
      )}
      ${adminDevicesTable(devices)}
    </section>

    <section class="dash-section" id="admin-asignaciones" data-dash-section>
      ${sectionHead(
        "VÍNCULOS",
        "Quién puede ver a quién",
        "Un vínculo permite que un entrenador o entrenador consulte las lecturas de un deportista. Puedes crear y desactivar vínculos."
      )}
      ${adminAssignmentForm(patients, members)}
      <div class="table-toolbar">
        <p class="dash-muted">${assignments.length} ${plural(assignments.length, "vínculo mostrado", "vínculos mostrados")}.</p>
        <label class="inline-check" for="assignments-include-inactive">
          <input type="checkbox" id="assignments-include-inactive" ${dashState.assignmentsIncludeInactive ? "checked" : ""} />
          <span>Mostrar vínculos inactivos</span>
        </label>
      </div>
      ${adminAssignmentsTable(assignments)}
    </section>`;
}

function adminUserForm() {
  return `<form id="user-form" class="assignment-form">
    <h3>Crear una cuenta</h3>
    <p class="dash-muted">Usa el correo institucional (por ejemplo, <code>@alumnos.udg.mx</code>). Genera una contraseña segura y entrégasela en persona.</p>
    <div class="form-row">
      <div class="field">
        <label for="user-name">Nombre completo</label>
        <input id="user-name" name="full_name" type="text" maxlength="120" required autocomplete="off" placeholder="Nombre y apellidos" />
      </div>
      <div class="field">
        <label for="user-email">Correo institucional</label>
        <input id="user-email" name="email" type="email" maxlength="160" required autocomplete="off" placeholder="nombre@alumnos.udg.mx" />
      </div>
      <div class="field">
        <label for="user-role">Rol</label>
        <select id="user-role" name="role">
          <option value="patient">Deportista</option>
          <option value="caregiver">Entrenador</option>
          <option value="specialist">Entrenador</option>
          <option value="administrador">Administrador</option>
          <option value="admin">Administrador</option>
        </select>
      </div>
      <div class="field">
        <label for="user-password">Contraseña asignada</label>
        <input id="user-password" name="password" type="text" autocomplete="off" required minlength="8" placeholder="Mínimo 8 caracteres, letras y números" />
        <button type="button" class="dash-button dash-button-quiet" data-for="user-password">Generar</button>
      </div>
      <button type="submit" class="dash-button dash-button-primary">Crear cuenta</button>
    </div>
    <p id="user-error" class="form-error hidden" role="alert"></p>
  </form>`;
}

function adminUsersTable(users) {
  if (!users.length) {
    return emptyState({
      title: "Sin cuentas registradas",
      text: "Crea la primera cuenta con el formulario de arriba.",
      icon: "users",
    });
  }

  const rows = users
    .map((user) => {
      const action = `<button type="button" class="dash-button dash-button-quiet" data-edit-user="${user.id}" aria-label="Editar la cuenta de ${escapeHtml(user.full_name)}">Editar</button>`;
      return `<tr class="${user.is_active ? "" : "is-inactive"}">
        <td><strong>${escapeHtml(user.full_name)}</strong><small>ID #${user.id}</small></td>
        <td>${escapeHtml(user.email)}</td>
        <td>${escapeHtml(roleLabel(user.role))}</td>
        <td>${statusPill(user.is_active ? "normal" : "no_data", user.is_active ? "Activa" : "Inactiva")}</td>
        <td>${escapeHtml(formatDateTime(user.created_at))}</td>
        <td><div class="table-actions">${action}</div></td>
      </tr>`;
    })
    .join("");

  return `<div class="table-wrap">
    <table>
      <caption>Cuentas del sistema. Puedes editar datos, rol, estado y contraseña.</caption>
      <thead>
        <tr>
          <th scope="col">Persona</th>
          <th scope="col">Correo</th>
          <th scope="col">Rol</th>
          <th scope="col">Estado</th>
          <th scope="col">Alta</th>
          <th scope="col">Acciones</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`;
}

function adminDevicesTable(devices) {
  if (!devices.length) {
    return emptyState({
      title: "Sin sensores registrados",
      text: "Todavía no hay dispositivos vinculados al sistema.",
      icon: "device",
    });
  }

  const rows = devices
    .map((device) => {
      const status = deviceAdminStatus(device);
      const toggleLabel = device.is_active ? "Desactivar" : "Activar";
      const toggleClass = device.is_active ? "dash-button-danger" : "dash-button-primary";
      return `<tr class="${device.is_active ? "" : "is-inactive"}">
        <td><strong>${escapeHtml(device.name)}</strong><small>${escapeHtml(device.device_id)}</small></td>
        <td>${escapeHtml(device.owner_name || "Sin propietario")}</td>
        <td>${escapeHtml(device.location || "Sin ubicación")}</td>
        <td>${statusPill(status.key, status.label)}</td>
        <td>${device.last_seen ? escapeHtml(formatRelative(device.last_seen)) : "Sin contacto"}</td>
        <td>
          <div class="table-actions">
            <button type="button" class="dash-button dash-button-quiet" data-edit-device="${device.id}" aria-label="Editar el sensor ${escapeHtml(device.name)}">Editar</button>
            <button type="button" class="dash-button ${toggleClass}" data-toggle-device="${device.id}" aria-label="${toggleLabel} el sensor ${escapeHtml(device.name)}">${toggleLabel}</button>
          </div>
        </td>
      </tr>`;
    })
    .join("");

  return `<div class="table-wrap">
    <table>
      <caption>Sensores registrados. Puedes editarlos o cambiar su estado.</caption>
      <thead>
        <tr>
          <th scope="col">Sensor</th>
          <th scope="col">Propietario</th>
          <th scope="col">Ubicación</th>
          <th scope="col">Estado</th>
          <th scope="col">Último contacto</th>
          <th scope="col">Acciones</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`;
}

function adminAssignmentForm(patients, members) {
  const canCreate = patients.length > 0 && members.length > 0;
  const disabled = canCreate ? "" : " disabled";
  const hint = !patients.length
    ? "No hay deportistas activos. Crea cuentas nuevas en la sección «Usuarios»."
    : !members.length
      ? "No hay entrenadores o entrenadors activos para vincular."
      : "El tipo de vínculo se toma del rol de la persona seleccionada.";

  return `<form id="assignment-form" class="assignment-form">
    <h3>Crear un vínculo</h3>
    <p class="dash-muted">Elige un deportista y la persona que lo acompañará. La otra persona solo verá las lecturas del deportista elegido.</p>
    <div class="form-row">
      <div class="field">
        <label for="assignment-patient">Deportista</label>
        <select id="assignment-patient" name="patient_id" required${disabled}>
          <option value="">Selecciona un deportista</option>
          ${patients.map(personOption).join("")}
        </select>
      </div>
      <div class="field">
        <label for="assignment-member">Entrenador o entrenador</label>
        <select id="assignment-member" name="member_id" required${disabled}>
          <option value="">Selecciona una persona</option>
          ${members.map(personOption).join("")}
        </select>
      </div>
      <button type="submit" class="dash-button dash-button-primary"${disabled}>Crear vínculo</button>
    </div>
    <p class="form-hint" id="assignment-hint">${escapeHtml(hint)}</p>
    <p id="assignment-error" class="form-error hidden" role="alert"></p>
  </form>`;
}

function adminAssignmentsTable(assignments) {
  if (!assignments.length) {
    return emptyState({
      title: "Sin vínculos para mostrar",
      text: "Crea un vínculo con el formulario de arriba o cambia el filtro para ver los inactivos.",
      icon: "link",
    });
  }

  const rows = assignments
    .map((assignment) => {
      const relationship = RELATIONSHIP_LABELS[assignment.relationship] ?? roleLabel(assignment.relationship);
      const action = assignment.is_active
        ? `<button type="button" class="dash-button dash-button-danger" data-deactivate-assignment="${assignment.id}" aria-label="Desactivar el vínculo entre ${escapeHtml(assignment.patient.full_name)} y ${escapeHtml(assignment.member.full_name)}">Desactivar</button>`
        : `<span class="dash-muted">Sin acciones</span>`;
      return `<tr class="${assignment.is_active ? "" : "is-inactive"}">
        <td><strong>${escapeHtml(assignment.patient.full_name)}</strong><small>Deportista</small></td>
        <td><strong>${escapeHtml(assignment.member.full_name)}</strong><small>${escapeHtml(roleLabel(assignment.member.role))}</small></td>
        <td>${escapeHtml(relationship)}</td>
        <td>${statusPill(assignment.is_active ? "normal" : "no_data", assignment.is_active ? "Activo" : "Inactivo")}</td>
        <td>${escapeHtml(formatDateTime(assignment.created_at))}</td>
        <td><div class="table-actions">${action}</div></td>
      </tr>`;
    })
    .join("");

  return `<div class="table-wrap">
    <table>
      <caption>Vínculos de cuidado.</caption>
      <thead>
        <tr>
          <th scope="col">Deportista</th>
          <th scope="col">Acompañante</th>
          <th scope="col">Tipo</th>
          <th scope="col">Estado</th>
          <th scope="col">Creado</th>
          <th scope="col">Acciones</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`;
}

async function submitPasswordForm(event) {
  event.preventDefault();
  const current = document.querySelector("#password-current").value;
  const nueva = document.querySelector("#password-new").value;
  const confirm = document.querySelector("#password-confirm").value;

  if (nueva !== confirm) {
    showFormError("password-error", "La contraseña nueva y su repetición no coinciden.");
    return;
  }
  if (nueva.length < 8 || !/[A-Za-z]/.test(nueva) || !/\d/.test(nueva)) {
    showFormError("password-error", "La contraseña nueva necesita mínimo 8 caracteres, con letras y números.");
    return;
  }
  if (nueva === current) {
    showFormError("password-error", "La contraseña nueva es igual a la actual.");
    return;
  }

  const button = event.target.querySelector("button[type='submit']");
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Guardando…";
  showFormError("password-error", "");

  try {
    await apiFetch("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: current, new_password: nueva }),
    });
    document.querySelector("#password-current").value = "";
    document.querySelector("#password-new").value = "";
    document.querySelector("#password-confirm").value = "";
    showToast("Tu contraseña se actualizó. Úsala en el próximo inicio de sesión.");
  } catch (error) {
    showFormError("password-error", friendlyError(error, "No pudimos actualizar tu contraseña."));
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

function passwordSegura() {
  const glyphs = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
  let value = "";
  do {
    value = Array.from({ length: 12 }, () => glyphs[Math.floor(Math.random() * glyphs.length)]).join("");
  } while (!/[A-Za-z]/.test(value) || !/\d/.test(value));
  return `${value}${Math.floor(Math.random() * 10)}`;
}

function openUserDialog(userId) {
  const user = dashState.users.find((item) => item.id === Number(userId));
  if (!user) {
    showToast("No encontramos esa cuenta. Actualiza la página e inténtalo de nuevo.", "error");
    return;
  }

  dashState.editingUserId = user.id;
  document.querySelector("#user-edit-name").value = user.full_name;
  document.querySelector("#user-edit-email").textContent = user.email;
  document.querySelector("#user-edit-role").value = user.role;
  document.querySelector("#user-edit-password").value = "";
  document.querySelector("#user-edit-active").checked = Boolean(user.is_active);
  showFormError("user-edit-form-error", "");
  openDialog("#user-dialog");
  window.setTimeout(() => document.querySelector("#user-edit-name").focus(), 30);
}

async function submitUserEditForm(event) {
  event.preventDefault();
  const userId = dashState.editingUserId;
  const user = dashState.users.find((item) => item.id === userId);
  if (!user) {
    showFormError("user-edit-form-error", "No encontramos esa cuenta. Cierra esta ventana y actualiza la página.");
    return;
  }

  const fullName = document.querySelector("#user-edit-name").value.trim();
  const role = document.querySelector("#user-edit-role").value;
  const isActive = document.querySelector("#user-edit-active").checked;
  const password = document.querySelector("#user-edit-password").value.trim();
  if (!fullName) {
    showFormError("user-edit-form-error", "Escribe un nombre completo.");
    return;
  }
  if (password && !/[A-Za-z]/.test(password)) {
    showFormError("user-edit-form-error", "La contraseña nueva necesita letras.");
    return;
  }
  if (password && !/\d/.test(password)) {
    showFormError("user-edit-form-error", "La contraseña nueva necesita números.");
    return;
  }

  const payload = { full_name: fullName, role, is_active: isActive };
  if (password) payload.password = password;

  const button = document.querySelector("#user-edit-save");
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Guardando…";
  showFormError("user-edit-form-error", "");

  try {
    await apiFetch(`/api/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    closeDialog("#user-dialog");
    showToast(password ? "Cuenta actualizada. Entrega la contraseña nueva en persona." : "Cuenta actualizada.");
    await loadRoleDashboard();
  } catch (error) {
    showFormError("user-edit-form-error", friendlyError(error, "No pudimos guardar los cambios de la cuenta."));
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

async function submitUserCreateForm(event) {
  event.preventDefault();
  const fullName = document.querySelector("#user-name").value.trim();
  const email = document.querySelector("#user-email").value.trim().toLowerCase();
  const role = document.querySelector("#user-role").value;
  const password = document.querySelector("#user-password").value;

  if (!fullName) {
    showFormError("user-error", "Escribe el nombre completo de la persona.");
    return;
  }
  if (!email || !email.includes("@")) {
    showFormError("user-error", "Escribe el correo institucional completo.");
    return;
  }
  if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    showFormError("user-error", "La contraseña necesita mínimo 8 caracteres, con letras y números.");
    return;
  }

  const button = document.querySelector("#user-form button[type='submit']");
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Creando…";
  showFormError("user-error", "");

  try {
    await apiFetch("/api/users", {
      method: "POST",
      body: JSON.stringify({ full_name: fullName, email, role, password }),
    });
    document.querySelector("#user-password").value = "";
    showToast("Cuenta creada. Entrega la contraseña en persona.");
    await loadRoleDashboard();
  } catch (error) {
    showFormError("user-error", friendlyError(error, "No pudimos crear la cuenta."));
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

function openDeviceDialog(deviceId) {
  const device = dashState.devices.find((item) => item.id === Number(deviceId));
  if (!device) {
    showToast("No encontramos ese sensor. Actualiza la página e inténtalo de nuevo.", "error");
    return;
  }

  dashState.editingDeviceId = device.id;
  document.querySelector("#device-name").value = device.name ?? "";
  document.querySelector("#device-location").value = device.location ?? "";
  document.querySelector("#device-code").textContent = device.device_id ?? "—";
  document.querySelector("#device-owner").textContent = device.owner_name || "Sin propietario";
  document.querySelector("#device-active").checked = Boolean(device.is_active);
  showFormError("device-form-error", "");
  openDialog("#device-dialog");
  window.setTimeout(() => document.querySelector("#device-name").focus(), 30);
}

async function submitDeviceForm(event) {
  event.preventDefault();
  const device = dashState.devices.find((item) => item.id === dashState.editingDeviceId);
  if (!device) {
    showFormError("device-form-error", "No encontramos ese sensor. Cierra esta ventana y actualiza la página.");
    return;
  }

  const name = document.querySelector("#device-name").value.trim();
  const location = document.querySelector("#device-location").value.trim();
  const isActive = document.querySelector("#device-active").checked;
  if (!name) {
    showFormError("device-form-error", "Escribe un nombre para el sensor.");
    document.querySelector("#device-name").focus();
    return;
  }

  const button = document.querySelector("#device-save");
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Guardando…";
  showFormError("device-form-error", "");

  try {
    await apiFetch(`/api/devices/${device.id}`, {
      method: "PATCH",
      body: JSON.stringify({ name, location: location || null, is_active: isActive }),
    });
    closeDialog("#device-dialog");
    showToast("Sensor actualizado.");
    await loadRoleDashboard();
  } catch (error) {
    showFormError("device-form-error", friendlyError(error, "No pudimos guardar los cambios del sensor."));
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

async function toggleDevice(deviceId) {
  const device = dashState.devices.find((item) => item.id === Number(deviceId));
  if (!device) {
    showToast("No encontramos ese sensor. Actualiza la página e inténtalo de nuevo.", "error");
    return;
  }

  const deactivating = device.is_active;
  const accepted = await askConfirm({
    title: deactivating ? "Desactivar sensor" : "Activar sensor",
    message: deactivating
      ? `El sensor «${device.name}» dejará de recibir lecturas nuevas. Las lecturas anteriores se conservan.`
      : `El sensor «${device.name}» volverá a recibir lecturas nuevas.`,
    confirmLabel: deactivating ? "Sí, desactivar" : "Sí, activar",
    danger: deactivating,
  });
  if (!accepted) return;

  try {
    await apiFetch(`/api/devices/${device.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !device.is_active }),
    });
    showToast(deactivating ? "Sensor desactivado." : "Sensor activado.");
    await loadRoleDashboard();
  } catch (error) {
    showToast(friendlyError(error, "No pudimos cambiar el estado del sensor."), "error");
  }
}

async function submitAssignmentForm(event) {
  event.preventDefault();
  const patientId = Number(document.querySelector("#assignment-patient").value);
  const memberId = Number(document.querySelector("#assignment-member").value);
  const member = dashState.users.find((user) => user.id === memberId);
  const patient = dashState.users.find((user) => user.id === patientId);

  if (!patient || !member) {
    showFormError("assignment-error", "Selecciona un deportista y una persona para acompañarlo.");
    return;
  }

  const button = document.querySelector("#assignment-form button[type='submit']");
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Creando…";
  showFormError("assignment-error", "");

  try {
    await apiFetch("/api/care/assignments", {
      method: "POST",
      body: JSON.stringify({
        patient_id: patient.id,
        member_id: member.id,
        relationship: member.role,
      }),
    });
    showToast(`Vínculo creado entre ${firstName(patient.full_name)} y ${firstName(member.full_name)}.`);
    await loadRoleDashboard();
  } catch (error) {
    showFormError("assignment-error", friendlyError(error, "No pudimos crear el vínculo."));
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

async function deactivateAssignment(assignmentId) {
  const assignment = dashState.assignments.find((item) => item.id === Number(assignmentId));
  if (!assignment) {
    showToast("No encontramos ese vínculo. Actualiza la página e inténtalo de nuevo.", "error");
    return;
  }

  const accepted = await askConfirm({
    title: "Desactivar vínculo",
    message: `¿Quieres quitar el vínculo entre ${assignment.patient.full_name} y ${assignment.member.full_name}? La persona dejará de ver las lecturas de este deportista. Las lecturas anteriores se conservan.`,
    confirmLabel: "Sí, desactivar",
    danger: true,
  });
  if (!accepted) return;

  try {
    await apiFetch(`/api/care/assignments/${assignment.id}`, { method: "DELETE" });
    showToast("Vínculo desactivado. La persona ya no verá las lecturas de este deportista.");
    await loadRoleDashboard();
  } catch (error) {
    showToast(friendlyError(error, "No pudimos desactivar el vínculo."), "error");
  }
}

function friendlyError(error, fallback = "No pudimos completar la acción. Revisa tu conexión e inténtalo de nuevo.") {
  const status = error?.status;
  if (status === 401) return "Tu sesión terminó. Vuelve a iniciar sesión.";
  if (status === 403) return "No tienes permiso para hacer esta acción.";
  if (status === 404) return "No encontramos ese registro. Actualiza la página e inténtalo de nuevo.";
  if (status === 409) return "Ese vínculo ya está activo.";
  if (status === 422) return "Revisa los datos. Hay un campo que no es válido.";
  return error?.message || fallback;
}

function showFormError(elementId, message) {
  const element = document.getElementById(elementId);
  if (!element) return;
  element.textContent = message;
  element.classList.toggle("hidden", !message);
}

// ============================================================================
// AUDITORÍA — EVENTOS, FILTROS Y EXPORTACIÓN
// ============================================================================

const AUDIT_STATUS_LABELS = {
  SUCCESS: "Correcto",
  DENIED: "Rechazado",
};

const AUDIT_ACTION_LABELS = {
  LOGIN: "Inicio de sesión",
  LOGOUT: "Cierre de sesión",
  ACCESS_DENIED: "Acceso rechazado",
  DEVICE_PROVISIONED: "Dispositivo aprovisionado",
  DEVICE_REGISTERED: "Dispositivo registrado",
  DEVICE_PAIRED: "Dispositivo vinculado",
  DEVICE_PAIR_FAILED: "Vinculación rechazada",
  DEVICE_KEY_ROTATED: "Clave de dispositivo rotada",
  DEVICE_UNPAIRED: "Dispositivo desvinculado",
  DEVICE_AUTH_FAILED: "Credencial de dispositivo rechazada",
  DEVICE_DATA_REJECTED: "Lectura de dispositivo rechazada",
};

async function loadAdministradorDashboard() {
  const filters = dashState.auditFilters;
  const params = new URLSearchParams({ limit: String(filters.limit) });
  if (filters.status) params.set("status", filters.status);
  if (filters.action) params.set("action", filters.action);

  const { data } = await apiFetch(`/api/audit?${params.toString()}`);
  dashState.audit = Array.isArray(data) ? data : [];
  renderAdministradorDashboard();
}

function renderAdministradorDashboard() {
  const content = document.querySelector("#dash-content");
  const events = dashState.audit;
  const filters = dashState.auditFilters;
  const denied = events.filter((event) => event.status === "DENIED");
  const successfulLogins = events.filter((event) => event.action === "LOGIN" && event.status === "SUCCESS");
  const last = events[0];

  let summary;
  if (denied.length) {
    summary = callout(
      "warning",
      "!",
      "Hay accesos rechazados",
      `<p>${denied.length} ${plural(denied.length, "evento aparece", "eventos aparecen")} como rechazado en esta vista. Revisa el detalle para saber si fue un error de contraseña o un intento sin permiso.</p><p>Un acceso rechazado no confirma por sí solo un incidente de seguridad.</p>`
    );
  } else if (events.length) {
    summary = callout(
      "success",
      "✓",
      "Sin accesos rechazados en esta vista",
      "<p>Los eventos cargados no incluyen accesos rechazados. Puedes cambiar los filtros para revisar otro período o tipo de evento.</p>"
    );
  } else {
    summary = callout(
      "info",
      "i",
      "No hay eventos para estos filtros",
      "<p>Prueba con otro resultado, otra acción o limpia los filtros para ver la actividad más reciente.</p>"
    );
  }

  content.innerHTML = `
    <section class="dash-section" id="resumen" data-dash-section>
      ${sectionHead(
        "AUDITORÍA",
        "Resumen de actividad",
        "Revisa inicios de sesión, cierres de sesión y accesos rechazados. Esta vista es de solo lectura."
      )}
      <div class="grid-4 section-gap-bottom">
        ${metricCard("Eventos cargados", String(events.length), `Límite: ${filters.limit}`)}
        ${metricCard("Accesos rechazados", String(denied.length), denied.length === 1 ? "Un evento" : "Eventos")}
        ${metricCard("Inicios correctos", String(successfulLogins.length), successfulLogins.length === 1 ? "Un inicio" : "Inicios")}
        ${metricCard("Último evento", last ? formatRelative(last.created_at) : "—", last ? formatDateTime(last.created_at) : "Sin eventos")}
      </div>
      ${summary}
    </section>

    <section class="dash-section" id="actividad" data-dash-section>
      ${sectionHead(
        "REGISTRO",
        "Eventos de administradoría",
        "Los eventos se muestran del más reciente al más antiguo. Puedes filtrar por resultado y por acción."
      )}
      ${auditFiltersForm(filters)}
      <div class="table-toolbar">
        <p class="dash-muted">Mostrando ${events.length} ${plural(events.length, "evento", "eventos")} con los filtros actuales.</p>
        <button type="button" class="dash-button dash-button-quiet" data-export-csv${events.length ? "" : " disabled"}>Exportar CSV</button>
      </div>
      ${auditTable(events)}
      <p class="reference-note">La exportación incluye hasta 200 eventos con los filtros actuales.</p>
    </section>`;
}

function auditFiltersForm(filters) {
  const statusOptions = [
    ["", "Todos los resultados"],
    ["SUCCESS", "Correcto"],
    ["DENIED", "Rechazado"],
  ];
  const actionOptions = [
    ["", "Todas las acciones"],
    ["LOGIN", "Inicio de sesión"],
    ["LOGOUT", "Cierre de sesión"],
    ["ACCESS_DENIED", "Acceso rechazado"],
    ["DEVICE_PAIRED", "Dispositivo vinculado"],
    ["DEVICE_PAIR_FAILED", "Vinculación rechazada"],
    ["DEVICE_KEY_ROTATED", "Clave de dispositivo rotada"],
    ["DEVICE_UNPAIRED", "Dispositivo desvinculado"],
    ["DEVICE_AUTH_FAILED", "Credencial de dispositivo rechazada"],
    ["DEVICE_DATA_REJECTED", "Lectura de dispositivo rechazada"],
  ];
  const limitOptions = [25, 50, 100, 200];

  const option = (value, label, current) =>
    `<option value="${value}"${String(value) === String(current) ? " selected" : ""}>${escapeHtml(label)}</option>`;

  return `<form id="audit-filters" class="filter-form">
    <div class="field">
      <label for="audit-status">Resultado</label>
      <select id="audit-status" name="status">
        ${statusOptions.map(([value, label]) => option(value, label, filters.status)).join("")}
      </select>
    </div>
    <div class="field">
      <label for="audit-action">Acción</label>
      <select id="audit-action" name="action">
        ${actionOptions.map(([value, label]) => option(value, label, filters.action)).join("")}
      </select>
    </div>
    <div class="field">
      <label for="audit-limit">Cantidad de eventos</label>
      <select id="audit-limit" name="limit">
        ${limitOptions.map((value) => option(value, String(value), filters.limit)).join("")}
      </select>
    </div>
    <button type="submit" class="dash-button dash-button-primary">Aplicar filtros</button>
    <button type="button" class="dash-button dash-button-quiet" data-clear-filters>Limpiar</button>
  </form>`;
}

function auditTable(events) {
  if (!events.length) {
    return emptyState({
      title: "Sin eventos de administradoría",
      text: "No hay eventos con estos filtros. Prueba con otro resultado u otra acción, o limpia la búsqueda.",
      actionLabel: "Limpiar filtros",
      actionAttr: "data-clear-filters",
      icon: "audit",
    });
  }

  const rows = events
    .map((event) => {
      const statusKey = event.status === "SUCCESS" ? "normal" : event.status === "DENIED" ? "critical" : "info";
      const statusLabel = AUDIT_STATUS_LABELS[event.status] ?? event.status;
      const actionLabel = AUDIT_ACTION_LABELS[event.action] ?? event.action;
      const person = event.email_attempted || (event.user_id ? `Usuario #${event.user_id}` : "Sin identificar");
      return `<tr>
        <td><strong>${escapeHtml(formatDateTime(event.created_at))}</strong><small>${escapeHtml(formatRelative(event.created_at))}</small></td>
        <td>${escapeHtml(person)}</td>
        <td>${escapeHtml(actionLabel)}</td>
        <td>${statusPill(statusKey, statusLabel)}</td>
        <td>${escapeHtml(event.detail || "Sin detalle")}</td>
        <td>${escapeHtml(event.ip_address || "—")}</td>
      </tr>`;
    })
    .join("");

  return `<div class="table-wrap">
    <table>
      <caption>Eventos de administradoría. Solo lectura.</caption>
      <thead>
        <tr>
          <th scope="col">Fecha y hora</th>
          <th scope="col">Persona</th>
          <th scope="col">Acción</th>
          <th scope="col">Resultado</th>
          <th scope="col">Detalle</th>
          <th scope="col">IP</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`;
}

async function exportAuditCsv(button) {
  const filters = dashState.auditFilters;
  const params = new URLSearchParams({ limit: "200" });
  if (filters.status) params.set("status", filters.status);
  if (filters.action) params.set("action", filters.action);

  const original = button?.textContent;
  if (button) {
    button.disabled = true;
    button.textContent = "Exportando…";
  }

  try {
    const { data } = await apiFetch(`/api/audit?${params.toString()}`);
    const events = Array.isArray(data) ? data : [];
    if (!events.length) {
      showToast("No hay eventos para exportar con estos filtros.", "error");
      return;
    }

    const rows = [
      ["Fecha y hora", "Persona", "Acción", "Resultado", "Detalle", "IP"],
      ...events.map((event) => [
        formatDateTime(event.created_at),
        event.email_attempted || (event.user_id ? `Usuario #${event.user_id}` : "Sin identificar"),
        AUDIT_ACTION_LABELS[event.action] ?? event.action,
        AUDIT_STATUS_LABELS[event.status] ?? event.status,
        event.detail || "Sin detalle",
        event.ip_address || "",
      ]),
    ];
    const csv = "\uFEFF" + rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `administradoria-biomonitor-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    showToast(`Se exportaron ${events.length} ${plural(events.length, "evento", "eventos")}.`);
  } catch (error) {
    showToast(friendlyError(error, "No pudimos exportar la administradoría."), "error");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = original;
    }
  }
}

function csvCell(value) {
  return `"${String(value ?? "").replace(/"/g, '""').replace(/\r?\n/g, " ")}"`;
}

// ============================================================================
// DIÁLOGOS Y CONFIRMACIONES
// ============================================================================

function openDialog(selector) {
  const dialog = typeof selector === "string" ? document.querySelector(selector) : selector;
  if (!dialog) return null;
  if (typeof dialog.showModal === "function") {
    if (!dialog.open) dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }
  return dialog;
}

function closeDialog(selector) {
  const dialog = typeof selector === "string" ? document.querySelector(selector) : selector;
  if (!dialog) return;
  if (typeof dialog.close === "function" && dialog.open) {
    dialog.close();
  } else {
    dialog.removeAttribute("open");
  }
}

function askConfirm({ title = "¿Estás seguro?", message = "", confirmLabel = "Sí, continuar", danger = true }) {
  return new Promise((resolve) => {
    dashState.confirmResolve = resolve;
    document.querySelector("#confirm-title").textContent = title;
    document.querySelector("#confirm-message").textContent = message;
    const accept = document.querySelector("#confirm-accept");
    accept.textContent = confirmLabel;
    accept.className = `dash-button ${danger ? "dash-button-danger" : "dash-button-primary"}`;
    openDialog("#confirm-dialog");
    document.querySelector("#confirm-cancel").focus();
  });
}

function resolveConfirm(value) {
  const resolve = dashState.confirmResolve;
  dashState.confirmResolve = null;
  closeDialog("#confirm-dialog");
  if (resolve) resolve(Boolean(value));
}

// ============================================================================
// EVENTOS DE LA INTERFAZ
// ============================================================================

function setMenuOpen(open) {
  primaryNav.classList.toggle("is-open", open);
  menuToggle.setAttribute("aria-expanded", String(open));
  menuToggle.setAttribute("aria-label", open ? "Cerrar menú" : "Abrir menú");
}

function closeMobileMenu() {
  setMenuOpen(false);
}

function setLoginMessage(text, info = false) {
  message.textContent = text;
  message.classList.toggle("is-info", info);
}

function loginErrorMessage(error) {
  if (error?.status === 401) {
    return "Correo o contraseña incorrectos. Revisa los datos e inténtalo de nuevo.";
  }
  if (error?.status === 422) {
    return "Revisa el correo y la contraseña. La contraseña debe tener al menos 8 caracteres.";
  }
  return "No pudimos conectar con el sistema. Revisa tu conexión e inténtalo de nuevo.";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoginMessage("Verificando identidad…", true);
  loginButton.disabled = true;
  try {
    await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: form.email.value.trim(),
        password: form.password.value,
      }),
    });
    const { data } = await apiFetch("/api/dashboard");
    setLoginMessage("");
    await showDashboard(data);
  } catch (error) {
    setLoginMessage(loginErrorMessage(error));
  } finally {
    loginButton.disabled = false;
  }
});

passwordToggle.addEventListener("click", () => {
  const password = form.password;
  const show = password.type === "password";
  password.type = show ? "text" : "password";
  passwordToggle.textContent = show ? "Ocultar" : "Mostrar";
  passwordToggle.setAttribute("aria-label", show ? "Ocultar contraseña" : "Mostrar contraseña");
  passwordToggle.setAttribute("aria-pressed", String(show));
});

document.querySelectorAll("[data-email]").forEach((button) => {
  button.addEventListener("click", (event) => {
    event.preventDefault();
    showLogin();
    form.email.value = button.dataset.email;
    form.password.value = "Practica4!";
    setLoginMessage(`Rol ${button.dataset.roleName} cargado. Presiona «Entrar al sistema».`, true);
    loginButton.focus();
  });
});

document.querySelectorAll("[data-view-link]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    if (link.dataset.viewLink === "login") showLogin();
    else showWelcome();
  });
});

menuToggle.addEventListener("click", () => {
  setMenuOpen(!primaryNav.classList.contains("is-open"));
});

document.addEventListener("click", (event) => {
  if (!primaryNav.classList.contains("is-open")) return;
  if (primaryNav.contains(event.target) || menuToggle.contains(event.target)) return;
  closeMobileMenu();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMobileMenu();
});

window.addEventListener("resize", () => {
  if (window.innerWidth > 900) closeMobileMenu();
});

primaryNav.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeMobileMenu);
});

window.addEventListener("hashchange", () => routeFromHash());

document.querySelector("#logout-button").addEventListener("click", logout);
document.querySelector("#account-logout").addEventListener("click", logout);

document.querySelector("#accessibility-button").addEventListener("click", () => {
  openDialog("#accessibility-dialog");
});

document.querySelector("#account-button").addEventListener("click", () => {
  openDialog("#account-dialog");
});

document.querySelector("#account-accessibility").addEventListener("click", () => {
  closeDialog("#account-dialog");
  openDialog("#accessibility-dialog");
});

document.querySelector("#refresh-button").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  const ok = await loadRoleDashboard();
  button.disabled = false;
  if (ok) showToast("Información actualizada.");
});

document.querySelector("#reset-prefs").addEventListener("click", () => {
  Object.assign(prefs, DEFAULT_PREFS);
  persistPrefs();
  applyPrefs();
  startAutoRefresh();
  showToast("Preferencias restablecidas.");
});

document.querySelector("#auto-refresh").addEventListener("change", (event) => {
  prefs.autoRefresh = event.currentTarget.checked;
  persistPrefs();
  startAutoRefresh();
});

document.querySelector("#device-form").addEventListener("submit", submitDeviceForm);
document.querySelector("#pair-form").addEventListener("submit", submitPairForm);

document.querySelector("#confirm-accept").addEventListener("click", () => resolveConfirm(true));
document.querySelector("#confirm-cancel").addEventListener("click", () => resolveConfirm(false));
document.querySelector("#confirm-close").addEventListener("click", () => resolveConfirm(false));

document.addEventListener("submit", (event) => {
  if (event.target.id === "assignment-form") {
    submitAssignmentForm(event);
  } else if (event.target.id === "user-form") {
    submitUserCreateForm(event);
  } else if (event.target.id === "user-edit-form") {
    submitUserEditForm(event);
  } else if (event.target.id === "password-form") {
    submitPasswordForm(event);
  } else if (event.target.id === "audit-filters") {
    event.preventDefault();
    dashState.auditFilters = {
      status: event.target.querySelector("#audit-status").value,
      action: event.target.querySelector("#audit-action").value,
      limit: Number(event.target.querySelector("#audit-limit").value) || 50,
    };
    loadRoleDashboard();
  }
});

document.addEventListener("change", (event) => {
  const historySelect = event.target.closest("[data-history-limit]");
  if (historySelect) {
    dashState.historyLimit = Number(historySelect.value) || 30;
    const dialog = document.querySelector("#patient-dialog");
    if (dialog?.open && dashState.detailPatientId) {
      openPatientDetail(dashState.detailPatientId);
    } else if (dashState.role === "patient") {
      loadRoleDashboard();
    }
    return;
  }
  if (event.target.id === "assignments-include-inactive") {
    dashState.assignmentsIncludeInactive = event.target.checked;
    loadRoleDashboard();
  }
  if (event.target.id === "assignment-member") {
    updateAssignmentHint();
  }
});

function updateAssignmentHint() {
  const select = document.querySelector("#assignment-member");
  const hint = document.querySelector("#assignment-hint");
  if (!select || !hint) return;
  const member = dashState.users.find((user) => user.id === Number(select.value));
  hint.textContent = member
    ? `Tipo de vínculo: ${roleLabel(member.role)}.`
    : "El tipo de vínculo se toma del rol de la persona seleccionada.";
}

function scrollToSection(sectionId) {
  const section = document.getElementById(sectionId);
  if (!section) return;
  const reduced = prefs.motion === "reduced" || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  section.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
  const heading = section.querySelector("h2");
  if (heading) heading.focus({ preventScroll: true });
  updateNavCurrent(sectionId);
}

function updateNavCurrent(sectionId) {
  document.querySelectorAll("#dash-nav [data-scroll], #bottom-nav [data-scroll]").forEach((button) => {
    if (button.dataset.scroll === sectionId) button.setAttribute("aria-current", "location");
    else button.removeAttribute("aria-current");
  });
}

function setupScrollSpy() {
  if (dashState.observer) {
    dashState.observer.disconnect();
    dashState.observer = null;
  }
  const sections = [...document.querySelectorAll("[data-dash-section]")];
  if (!sections.length || !("IntersectionObserver" in window)) return;

  dashState.observer = new IntersectionObserver(
    (entries) => {
      const current = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (current) updateNavCurrent(current.target.id);
    },
    { rootMargin: "-20% 0px -55% 0px", threshold: [0, 0.2, 0.5, 1] }
  );

  sections.forEach((section) => dashState.observer.observe(section));
}

async function testPermission(resource) {
  const paths = {
    users: "/api/users",
    audit: "/api/audit?limit=10",
    devices: "/api/devices",
    care: "/api/care/patients",
  };
  const path = paths[resource] ?? "/api/dashboard";
  apiResult.textContent = `GET ${path}\nSolicitando…`;
  try {
    const { status, data } = await apiFetch(path);
    apiResult.textContent = `GET ${path}\nHTTP ${status} — AUTORIZADO\n\n${JSON.stringify(data, null, 2)}`;
  } catch (error) {
    const detail = error.data ?? { detail: error.message };
    apiResult.textContent = `GET ${path}\nHTTP ${error.status ?? "Error"} — ACCESO RECHAZADO\n\n${JSON.stringify(detail, null, 2)}`;
  }
}

document.addEventListener("click", (event) => {
  const target = event.target instanceof Element ? event.target : null;
  if (!target) return;

  const closeButton = target.closest("[data-close-dialog]");
  if (closeButton) {
    event.preventDefault();
    const dialog = closeButton.closest("dialog");
    if (dialog?.id === "confirm-dialog") resolveConfirm(false);
    else closeDialog(dialog);
    return;
  }

  const legalButton = target.closest("[data-open-legal]");
  if (legalButton) {
    event.preventDefault();
    openDialog(`#${legalButton.dataset.openLegal}`);
    return;
  }

  const dialogButton = target.closest("[data-dialog]");
  if (dialogButton) {
    event.preventDefault();
    openDialog(`#${dialogButton.dataset.dialog}`);
    return;
  }

  const helpButton = target.closest("[data-open-help]");
  if (helpButton) {
    event.preventDefault();
    openDialog("#help-dialog");
    return;
  }

  const pairButton = target.closest("[data-open-pair]");
  if (pairButton) {
    event.preventDefault();
    openPairDialog();
    return;
  }

  const scrollButton = target.closest("[data-scroll]");
  if (scrollButton) {
    event.preventDefault();
    scrollToSection(scrollButton.dataset.scroll);
    return;
  }

  const textSizeButton = target.closest("[data-text-size]");
  if (textSizeButton) {
    prefs.textSize = textSizeButton.dataset.textSize;
    persistPrefs();
    applyPrefs();
    return;
  }

  const contrastButton = target.closest("[data-contrast]");
  if (contrastButton) {
    prefs.contrast = contrastButton.dataset.contrast;
    persistPrefs();
    applyPrefs();
    return;
  }

  const motionButton = target.closest("[data-motion]");
  if (motionButton) {
    prefs.motion = motionButton.dataset.motion;
    persistPrefs();
    applyPrefs();
    return;
  }

  const patientButton = target.closest("[data-patient-id]");
  if (patientButton) {
    event.preventDefault();
    openPatientDetail(Number(patientButton.dataset.patientId));
    return;
  }

  const patientRetry = target.closest("[data-patient-retry]");
  if (patientRetry) {
    event.preventDefault();
    openPatientDetail(Number(patientRetry.dataset.patientRetry));
    return;
  }

  const retryButton = target.closest("[data-retry]");
  if (retryButton) {
    event.preventDefault();
    loadRoleDashboard({ initial: true });
    return;
  }

  const editDeviceButton = target.closest("[data-edit-device]");
  if (editDeviceButton) {
    event.preventDefault();
    openDeviceDialog(Number(editDeviceButton.dataset.editDevice));
    return;
  }

  const editUserButton = target.closest("[data-edit-user]");
  if (editUserButton) {
    event.preventDefault();
    openUserDialog(Number(editUserButton.dataset.editUser));
    return;
  }

  const generatePasswordButton = target.closest(".dash-button.dash-button-quiet[data-for]");
  if (generatePasswordButton) {
    event.preventDefault();
    const field = document.getElementById(generatePasswordButton.dataset.for);
    if (field) {
      field.value = passwordSegura();
      field.focus();
      showToast("Contraseña generada. Cópiala antes de crear otra: se muestra solo aquí.");
    }
  }

  const dialogGeneratePassword = target.closest("#generate-user-password");
  if (dialogGeneratePassword) {
    event.preventDefault();
    const field = document.querySelector("#user-edit-password");
    field.value = passwordSegura();
    field.focus();
    showToast("Contraseña generada. Cópiala antes de cerrar: no vuelve a mostrarse.");
  }

  const toggleDeviceButton = target.closest("[data-toggle-device]");
  if (toggleDeviceButton) {
    event.preventDefault();
    toggleDevice(Number(toggleDeviceButton.dataset.toggleDevice));
    return;
  }

  const unpairDeviceButton = target.closest("[data-unpair-device]");
  if (unpairDeviceButton) {
    event.preventDefault();
    unpairDevice(Number(unpairDeviceButton.dataset.unpairDevice));
    return;
  }

  const deactivateButton = target.closest("[data-deactivate-assignment]");
  if (deactivateButton) {
    event.preventDefault();
    deactivateAssignment(Number(deactivateButton.dataset.deactivateAssignment));
    return;
  }

  const exportButton = target.closest("[data-export-csv]");
  if (exportButton) {
    event.preventDefault();
    exportAuditCsv(exportButton);
    return;
  }

  const clearFilters = target.closest("[data-clear-filters]");
  if (clearFilters) {
    event.preventDefault();
    dashState.auditFilters = { status: "", action: "", limit: 50 };
    loadRoleDashboard();
    return;
  }

  const actionButton = target.closest("[data-action]");
  if (actionButton) {
    event.preventDefault();
    testPermission(actionButton.dataset.action);
  }
});

document.querySelectorAll("dialog").forEach((dialog) => {
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    if (dialog.id === "confirm-dialog") resolveConfirm(false);
    else closeDialog(dialog);
  });

  dialog.addEventListener("cancel", (event) => {
    if (dialog.id === "confirm-dialog") {
      event.preventDefault();
      resolveConfirm(false);
    }
  });
});

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

loadPrefs();
applyPrefs();

(async function init() {
  const restored = await loadSession();
  if (!restored) routeFromHash({ focus: false });
})();
// --- Cronómetro de apnea (calmado, sin alertas) ---
let apneaTimerInterval = null;
let apneaTimerStart = 0;
let apneaTimerElapsed = 0;
let apneaTimerRunning = false;

function formatApneaTimer(ms) {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function currentApneaElapsed() {
  return apneaTimerElapsed + (apneaTimerRunning ? Date.now() - apneaTimerStart : 0);
}

function updateApneaTimerDisplay() {
  const el = document.querySelector("#apnea-timer-display");
  if (el) el.textContent = formatApneaTimer(currentApneaElapsed());
}

function startApneaTimer() {
  if (apneaTimerRunning) return;
  apneaTimerRunning = true;
  apneaTimerStart = Date.now();
  apneaTimerInterval = window.setInterval(updateApneaTimerDisplay, 250);
  updateApneaTimerDisplay();
}

function pauseApneaTimer() {
  if (!apneaTimerRunning) return;
  apneaTimerElapsed += Date.now() - apneaTimerStart;
  apneaTimerRunning = false;
  if (apneaTimerInterval) window.clearInterval(apneaTimerInterval);
  apneaTimerInterval = null;
  updateApneaTimerDisplay();
}

function resetApneaTimer() {
  pauseApneaTimer();
  apneaTimerElapsed = 0;
  updateApneaTimerDisplay();
}

function updateApneaSemaphore(spo2) {
  const el = document.querySelector("#apnea-semaphore");
  const text = document.querySelector("#apnea-semaphore-text");
  if (!el || !text) return;
  let cls = "is-green";
  let label = "Oxigeno en rango";
  if (spo2 === null || spo2 === undefined) {
    cls = "is-gray";
    label = "Sin lectura";
  } else if (spo2 < 90) {
    cls = "is-red";
    label = "Oxigeno bajo";
  } else if (spo2 < 95) {
    cls = "is-yellow";
    label = "Oxigeno un poco bajo";
  }
  el.className = `apnea-semaphore ${cls}`;
  text.textContent = label;
}

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  if (target.id === "apnea-start") startApneaTimer();
  if (target.id === "apnea-pause") pauseApneaTimer();
  if (target.id === "apnea-reset") resetApneaTimer();
});

// ============================================================================
// RESPIRACIÓN GUIADA (box breathing / 4-7-8 / diafragmática)
// ============================================================================
let breathInterval = null;
let breathRunning = false;
let breathStepIndex = 0;
let breathStepStart = 0;
const BREATH_TYPE = "box"; // se puede cambiar a "4-7-8" o "diafragmatica"

function breathSteps() {
  return breathingCycles(BREATH_TYPE);
}

function breathUpdateUI() {
  const steps = breathSteps();
  const step = steps[breathStepIndex];
  if (!step) return;
  const text = document.querySelector(".breathing-text");
  const phase = document.querySelector("#breath-phase");
  const ring = document.querySelector(".breathing-ring");
  const inhale = step.name.toLowerCase().includes("inalar");
  const exhale = step.name.toLowerCase().includes("exhalar");
  if (text) text.innerHTML = step.name + ` <span>${step.s}s</span>`;
  if (phase) phase.textContent = step.name;
  if (ring) {
    ring.style.animationDuration = step.s + "s";
    ring.style.animationName = inhale ? "breath-expand" : exhale ? "breath-contract" : "breath-hold";
  }
}

function breathStart() {
  if (breathRunning) return;
  breathRunning = true;
  breathStepIndex = 0;
  breathStepStart = Date.now();
  breathUpdateUI();
  breathInterval = setInterval(() => {
    const steps = breathSteps();
    const step = steps[breathStepIndex];
    if (!step) return;
    const elapsed = Date.now() - breathStepStart;
    if (elapsed >= step.s * 1000) {
      breathStepIndex = (breathStepIndex + 1) % steps.length;
      breathStepStart = Date.now();
      breathUpdateUI();
    }
  }, 200);
}

function breathPause() {
  if (!breathRunning) return;
  breathRunning = false;
  if (breathInterval) clearInterval(breathInterval);
  breathInterval = null;
}

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  if (target.id === "breath-start") breathStart();
  if (target.id === "breath-pause") breathPause();
});

// Panel de Atalaya (administracion). Todo contenido dinamico se inserta con
// textContent o nodos creados a mano (nunca innerHTML), asi que el texto de un correo
// o de una cabecera no puede ejecutar codigo. Los anchos de las barras se asignan con
// style.setProperty (la CSP no permite atributos style).
"use strict";

const RISK_TEXT = { high: "Alta", medium: "Media", low: "Baja", safe: "Limpio" };
const STATUS_TEXT = {
  new: "Nuevo",
  labeled: "Etiquetado",
  pending_approval: "Pendiente",
  quarantined: "Cuarentena",
  dismissed: "Sin acción",
};
const ACTION_TEXT = {
  quarantine: "Puso el correo en cuarentena",
  reject_quarantine: "Decidió no aislarlo y dejarlo donde estaba",
  mark_legit: "Lo devolvió a la bandeja como legítimo",
};
const REVIEW_OUTCOME = {
  mark_legit: "Legítimo",
  reject_quarantine: "Sin aislar",
};
const INVITE_TEXT = { pending: "Pendiente", used: "Usada", expired: "Vencida", revoked: "Revocada" };
const VIEWS = {
  panel: "Panel de Control",
  analitica: "Analítica y Tráfico",
  buzones: "Usuarios Conectados",
  historial: "Historial de Amenazas",
  politica: "Configuración de Auditoría",
};
const OLD_HASHES = { correos: "panel", resumen: "panel" }; // enlaces de versiones anteriores

// lastHuman, riskKey, finalState y FILTERS viven en estado.js (se carga antes que este archivo).

// --- Estado de la vista (solo del navegador; no son datos de correos) ---
let allAlerts = [];
let lastAlerts = []; // con el filtro de buzon
let campaignList = [];
let lastCoverage = [];
let events = [];
let policy = { medium: 30, high: 60 };
let selectedId = null;
let subTab = "forense";
let currentView = "panel";
let myName = "";
const PAGE = 24;
const AREAS = ["Gerencia/Dirección", "Finanzas", "Recursos Humanos", "Ventas y Compras", "Operaciones y Logística", "IT y Sistemas", "Sin área"];
const ui = { area: "", filter: "all", query: "", limit: 40, listaLimit: PAGE, historyLimit: 40, buzonFilter: "all", buzonQuery: "", rango: "7d", analiticaLimit: PAGE };
const norm = (t) => t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const matches = (c, q) => !q || norm(c.label + " " + c.account).includes(norm(q));
const scoreOf = (a) => a.signals.reduce((n, s) => n + s.weight, 0);

const msgEl = document.getElementById("mensaje");
const covEl = document.getElementById("coverage");
const filtroEl = document.getElementById("filtro");
const areaEl = document.getElementById("filtro-area");
const listaEl = document.getElementById("lista-correos");
const cuerpoEl = document.getElementById("detalle-cuerpo");
const wide = window.matchMedia("(min-width: 1100px)");

let mode = "demo";
let authRequired = false;
let multiple = false;
let readOnly = false; // rol de supervisor: el servidor tambien lo hace cumplir (403)

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

const SVG_NS = "http://www.w3.org/2000/svg";
function icon(name) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "ico");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttribute("href", "/static/icons/sprite.svg#i-" + name);
  svg.appendChild(use);
  return svg;
}

function button(label, cls, onClick) {
  const b = el("button", cls, label);
  b.type = "button";
  b.addEventListener("click", onClick);
  return b;
}

// Aviso flotante con el resultado de cada accion (visible aunque la persona este mas abajo)
let toastTimer = null;
function say(text, kind) {
  msgEl.textContent = text;
  msgEl.className = "mensaje toast" + (kind ? " " + kind : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { msgEl.textContent = ""; }, kind === "error" ? 12000 : 7000);
}

// Mientras una accion se procesa, su boton queda desactivado y lo dice
async function busy(btn, work) {
  const label = btn ? btn.textContent : "";
  if (btn) { btn.disabled = true; btn.classList.add("ocupado"); btn.textContent = "Procesando…"; }
  try {
    return await work();
  } finally {
    if (btn && btn.isConnected) { btn.disabled = false; btn.classList.remove("ocupado"); btn.textContent = label; }
  }
}

function emptyState(glyph, title, text, action) {
  const box = el("div", "vacio");
  box.appendChild(el("div", "icono", glyph));
  box.appendChild(el("strong", "", title));
  if (text) box.appendChild(el("p", "", text));
  if (action) box.appendChild(action);
  return box;
}

async function api(path, method = "GET", body) {
  const headers = { "X-Requested-With": "atalaya" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401 && authRequired) {
    window.location.href = "/login";
    throw new Error("Inicia sesión.");
  }
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail;
    throw new Error(typeof detail === "string" ? detail : "Algo salió mal.");
  }
  return res.json();
}

function formatDate(iso) {
  return new Date(iso).toLocaleString("es-PA", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}
const formatTime = (iso) => new Date(iso).toLocaleTimeString("es-PA", { hour: "2-digit", minute: "2-digit", hour12: false });
const formatDay = (iso) => new Date(iso).toLocaleDateString("es-PA", { day: "numeric", month: "short" });

function statusText(alert) {
  if (alert.status === "quarantined") return STATUS_TEXT.quarantined;
  if (alert.reviewed) {
    const human = lastHuman(alert);
    if (human && REVIEW_OUTCOME[human]) return REVIEW_OUTCOME[human];
  }
  return STATUS_TEXT[alert.status];
}

function actionLabel(action) {
  if (action.type.startsWith("label:")) return "Etiqueta «" + action.type.slice(6) + "»";
  return ACTION_TEXT[action.type] || action.type;
}

function actorLabel(actor) {
  if (actor === "sistema" || actor === "atalaya") return "Atalaya";
  if (actor === "desconocido") return "Persona sin identificar";
  if (actor === "admin-demo") return demoPerson();
  return actor;
}
const demoPerson = () => (mode === "demo" ? "Carlos Mendoza (demo)" : "Administración");

function riskBadge(a, long) {
  const k = riskKey(a);
  const cls = k === "safe" ? "ok" : k;
  return el("span", "badge " + cls, (long ? "Amenaza " : "") + RISK_TEXT[k].toLowerCase().replace(/^./, (c) => c.toUpperCase()));
}

// --- Navegacion entre vistas y paneles -------------------------------------------------------
function setMenu(open, focus) {
  document.body.classList.toggle("menu-abierto", open);
  document.getElementById("menu-abrir").setAttribute("aria-expanded", String(open));
  if (open && focus) document.querySelector("#menu .nav-btn[aria-current]").focus();
  if (!open && focus) document.getElementById("menu-abrir").focus();
}

function showView(name) {
  if (OLD_HASHES[name]) name = OLD_HASHES[name];
  if (!VIEWS[name]) name = "panel";
  currentView = name;
  document.body.dataset.vista = name;
  Object.keys(VIEWS).forEach((v) => {
    document.getElementById("vista-" + v).hidden = v !== name;
    const btn = document.getElementById("nav-" + v);
    if (v === name) btn.setAttribute("aria-current", "page"); else btn.removeAttribute("aria-current");
  });
  document.getElementById("titulo-vista").textContent = VIEWS[name];
  document.title = VIEWS[name] + " — Atalaya";
  if (name !== "panel") closeDetail(false);
  if (name === "analitica") renderAnalytics();
  document.body.classList.remove("menu-abierto");
  document.getElementById("menu-abrir").setAttribute("aria-expanded", "false");
  document.getElementById("contenido").scrollTop = 0;
  if (window.location.hash !== "#" + name) history.replaceState(null, "", "#" + name);
}
document.querySelectorAll("#menu .nav-btn").forEach((b) => b.addEventListener("click", () => showView(b.dataset.vista)));
document.getElementById("menu-abrir").addEventListener("click", () => setMenu(true, true));
document.getElementById("menu-cerrar").addEventListener("click", () => setMenu(false, true));
document.getElementById("velo").addEventListener("click", () => { setMenu(false, false); closeDetail(true); });

let detOpener = null;
function openDetail(id, opener) {
  selectedId = id;
  detOpener = opener || null;
  renderList();
  renderDetail();
  document.body.classList.add("det-abierto");
  cuerpoEl.scrollTop = 0;
  if (!wide.matches) document.getElementById("detalle-cerrar").focus();
}

function closeDetail(restoreFocus) {
  const had = document.body.classList.contains("det-abierto");
  selectedId = null;
  document.body.classList.remove("det-abierto");
  if (currentView === "panel" && had) { renderList(); renderDetail(); }
  if (restoreFocus && had && detOpener && detOpener.isConnected) detOpener.focus();
  else if (restoreFocus && had) listaEl.querySelector(".fila-btn")?.focus();
}
document.getElementById("detalle-cerrar").addEventListener("click", () => closeDetail(true));
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape" || document.querySelector("dialog[open]")) return;
  if (document.body.classList.contains("menu-abierto")) setMenu(false, true);
  else if (document.body.classList.contains("det-abierto") && !wide.matches) closeDetail(true);
});
wide.addEventListener("change", () => { if (wide.matches) document.body.classList.remove("det-abierto"); });

// --- Lista de correos ----------------------------------------------------------------------
function renderFilters() {
  const box = document.getElementById("filtros");
  box.replaceChildren();
  FILTERS.forEach((f) => {
    const n = lastAlerts.filter(f.match).length;
    const b = el("button", "filtro " + f.cls);
    b.type = "button";
    b.append(document.createTextNode(f.label), el("span", "n", String(n)));
    b.setAttribute("aria-pressed", String(ui.filter === f.key));
    b.addEventListener("click", () => { ui.filter = f.key; ui.limit = 40; renderFilters(); renderList(); });
    box.appendChild(b);
  });
}

function visibleAlerts() {
  const f = FILTERS.find((x) => x.key === ui.filter) || FILTERS[0];
  const q = norm(ui.query.trim());
  return lastAlerts
    .filter(f.match)
    .filter((a) => !q || norm(a.sender_domain + " " + a.mailbox_label).includes(q))
    .sort((a, b) => a.priority - b.priority || b.received_at.localeCompare(a.received_at));
}

const accountOf = (id) => (lastCoverage.find((c) => c.mailbox_id === id) || {}).account || "";

function cell(...kids) {
  const c = el("span", "celda");
  c.setAttribute("role", "presentation");
  kids.forEach((k) => c.appendChild(k));
  return c;
}

function renderRow(a) {
  const k = riskKey(a);
  const li = el("div", "fila-correo " + k);
  li.setAttribute("role", "listitem");
  const b = el("button", "fila-btn");
  b.type = "button";
  if (a.id === selectedId) b.setAttribute("aria-current", "true");
  // riesgo / score
  const rc = el("span", "riesgo-celda");
  const rf = el("span", "riesgo-fila");
  rf.appendChild(riskBadge(a, false));
  const sc = el("span", "score", String(scoreOf(a)));
  sc.appendChild(el("small", "", " pts"));
  rf.appendChild(sc);
  const bar = el("span", "barra-puntaje");
  const fill = el("span");
  fill.style.setProperty("--w", Math.min(100, scoreOf(a)) + "%");
  bar.appendChild(fill);
  rc.append(rf, bar);
  // empleado, remitente, vector, hora, estado
  const emp = cell(el("span", "celda-1", a.mailbox_label || "—"), el("span", "celda-2", a.department + " · " + accountOf(a.mailbox_id)));
  const ip = a.ficha && a.ficha.source_ip ? "IP " + a.ficha.source_ip : "";
  const rem = cell(el("span", "celda-1", a.sender_domain || "—"), el("span", "celda-2", ip));
  const vec = el("span", "celda c-vector");
  vec.append(el("span", "celda-1", a.vector), el("span", "celda-2 sans", a.signals.length + (a.signals.length === 1 ? " señal" : " señales")));
  vec.title = a.vector;
  const hora = el("span", "celda der");
  hora.append(el("span", "celda-1", formatTime(a.received_at)), el("span", "celda-2", formatDay(a.received_at)));
  const est = el("span", "celda der");
  est.appendChild(el("span", a.status === "pending_approval" ? "badge decidir" : "badge estado", statusText(a)));
  b.append(rc, emp, rem, vec, hora, est);
  b.addEventListener("click", (e) => openDetail(a.id, e.currentTarget));
  li.appendChild(b);
  return li;
}

function renderList() {
  const items = visibleAlerts();
  const shown = items.slice(0, ui.limit);
  listaEl.replaceChildren(...shown.map(renderRow));
  listaEl.removeAttribute("aria-busy");
  const more = document.getElementById("correos-mas");
  more.hidden = items.length <= shown.length;
  more.textContent = "Mostrar más (" + (items.length - shown.length) + ")";
  document.getElementById("lista-resumen").textContent = items.length
    ? "Mostrando " + shown.length + " de " + items.length + (items.length === 1 ? " correo" : " correos") + (multiple ? " · " + lastCoverage.length + " buzones vigilados" : "")
    : "";
  if (!lastAlerts.length) {
    listaEl.appendChild(emptyState("✓", "Bandeja tranquila", filtroEl.value
      ? "Este buzón no tiene correos por revisar."
      : "Atalaya aún no ha marcado ningún correo. Cuando llegue uno sospechoso, aparecerá aquí con su explicación."));
  } else if (!items.length) {
    listaEl.appendChild(emptyState("⌕", "No hay eventos que coincidan con este filtro", "Prueba con otro filtro o limpia el buscador.",
      button("Restablecer filtros", "btn", () => { ui.filter = "all"; ui.query = ""; document.getElementById("buscar-correos").value = ""; renderFilters(); renderList(); })));
  }
}
document.getElementById("buscar-correos").addEventListener("input", (e) => { ui.query = e.target.value; ui.limit = 40; renderList(); });
document.getElementById("correos-mas").addEventListener("click", () => { ui.limit += 40; renderList(); });
document.querySelectorAll(".kpi").forEach((k) => k.addEventListener("click", () => {
  ui.filter = k.dataset.kpi; ui.limit = 40; renderFilters(); renderList();
  document.getElementById("filtros").scrollIntoView({ block: "start" });
}));

// --- Inspector del correo ------------------------------------------------------------------
function detailEmpty() {
  const box = el("div", "det-vacio");
  box.appendChild(icon("shield-check"));
  box.appendChild(el("strong", "", "Elige un correo de la lista"));
  box.appendChild(el("p", "", "Aquí verás por qué Atalaya desconfía de él, su ficha técnica y qué puedes hacer."));
  return box;
}

const SOURCE_TEXT = { ai: "Resumen con IA", simulated: "Resumen simulado (sin IA real)", rules: "Reglas de Atalaya" };

function whyBlock(alert) {
  const frag = document.createDocumentFragment();
  const h = el("h3", "det-h");
  h.append(el("span", "", "¿Por qué Atalaya detectó esta amenaza?"), icon("shield-alert"));
  frag.appendChild(h);
  if (alert.explanation_source !== "rules") {
    const resumen = el("p", "resumen-ia");
    resumen.appendChild(el("span", "tag", SOURCE_TEXT[alert.explanation_source] || "Resumen"));
    resumen.appendChild(document.createTextNode(alert.explanation.replace(/^Resumen simulado:\s*/, "")));
    frag.appendChild(resumen);
  }
  if (!alert.signals.length) {
    frag.appendChild(el("p", "det-nota", "Atalaya no encontró nada sospechoso en este correo."));
  } else {
    const ol = el("ol", "por-que");
    alert.signals.slice().sort((a, b) => b.weight - a.weight).forEach((s) => {
      const li = el("li", "");
      const t = el("span", "", s.description);
      t.appendChild(el("span", "peso", "+" + s.weight + " puntos · " + s.vector));
      li.appendChild(t);
      ol.appendChild(li);
    });
    frag.appendChild(ol);
    frag.appendChild(el("p", "det-nota", "Los hechos (SPF, DKIM, DMARC, dominios parecidos, enlaces) los calcula el código de Atalaya. La IA solo redacta el resumen."));
  }
  if (alert.actions.length) {
    frag.appendChild(el("h3", "det-h mono-t", "Qué pasó con este correo"));
    const ul = el("ul", "linea");
    alert.actions.forEach((a) => {
      const li = el("li", "");
      li.appendChild(el("span", "muted", formatDate(a.at) + " · "));
      li.appendChild(el("strong", "", actorLabel(a.by) + ": "));
      li.appendChild(document.createTextNode(actionLabel(a)));
      if (a.reason) li.appendChild(el("div", "motivo", "Motivo: " + a.reason));
      ul.appendChild(li);
    });
    frag.appendChild(ul);
  }
  return frag;
}

const NO_FICHA = "Sin datos técnicos guardados para este correo (es anterior a esta función).";

function smtpBlock(alert) {
  const frag = document.createDocumentFragment();
  const h = el("h3", "det-h mono-t");
  h.appendChild(el("span", "", "Cabeceras técnicas SMTP / MIME"));
  const f = alert.ficha;
  if (f && f.smtp.length) h.appendChild(button("Copiar", "btn-mini", () => copyText(f.smtp.join("\n"), "Cabeceras copiadas.")));
  frag.appendChild(h);
  if (!f || !f.smtp.length) {
    frag.appendChild(el("div", "sin-datos", f ? "No se guardaron cabeceras para este correo." : NO_FICHA));
  } else {
    frag.appendChild(el("pre", "smtp", f.smtp.join("\n")));
  }
  frag.appendChild(el("p", "det-nota", "Solo se guardan cabeceras técnicas saneadas: sin direcciones de correo completas, sin asunto y sin cuerpo."));
  return frag;
}

async function copyText(text, okMsg) {
  try {
    await navigator.clipboard.writeText(text);
    say(okMsg, "ok");
  } catch {
    say("No se pudo copiar: selecciona el texto y usa Ctrl + C.", "error");
  }
}

const AUTH_CLASS = { pass: "pass", fail: "fail", softfail: "soft", none: "", neutral: "" };

function fichaBlock(alert) {
  const f = alert.ficha;
  const box = el("div", "det-ficha");
  const cab = el("div", "ficha-cab");
  const t = el("h3", "ficha-t");
  t.append(icon("cpu"), document.createTextNode("Ficha técnica del mensaje"));
  cab.appendChild(t);
  if (f) {
    cab.appendChild(button("Copiar IoC", "btn-mini", () => {
      const lines = ["dominio_remitente: " + alert.sender_domain];
      if (f.source_ip) lines.push("ip_origen: " + f.source_ip);
      if (f.return_path) lines.push("return_path: " + f.return_path);
      if (f.reply_to_domain) lines.push("reply_to_dominio: " + f.reply_to_domain);
      f.link_hosts.forEach((h) => lines.push("url: " + h));
      copyText(lines.join("\n"), "Indicadores copiados (todo neutralizado).");
    }));
  }
  box.appendChild(cab);
  if (!f) { box.appendChild(el("div", "sin-datos", NO_FICHA)); return box; }
  const grid = el("div", "ficha-grid");
  const auth = el("div", "f-cel ancho fila");
  auth.appendChild(el("span", "f-et", "Autenticación"));
  const badges = el("div", "auth-badges");
  [["SPF", f.spf], ["DKIM", f.dkim], ["DMARC", f.dmarc]].forEach(([n, v]) => {
    badges.appendChild(el("span", "auth-b " + (AUTH_CLASS[v] || ""), n + ":" + (v ? v.toUpperCase() : "—")));
  });
  auth.appendChild(badges);
  grid.appendChild(auth);
  const card = (label, value, cls, wide2) => {
    const c = el("div", "f-cel" + (wide2 ? " ancho" : ""));
    c.append(el("span", "f-et", label), el("span", "f-val " + (cls || ""), value));
    return c;
  };
  const ip = card("IP de origen y país", (f.source_ip || "no encontrada") + " · —");
  ip.title = "El país no se consulta: Atalaya no usa servicios externos de geolocalización.";
  grid.appendChild(ip);
  grid.appendChild(card("Vector de ataque", alert.vector, "sans"));
  grid.appendChild(card("Return-Path real", f.return_path || "—", "", true));
  if (f.reply_to_domain) grid.appendChild(card("Reply-To (dominio)", f.reply_to_domain, "", true));
  grid.appendChild(card("URL detectada (neutralizada)", f.link_hosts.length ? f.link_hosts.join("  ") : "Sin enlaces", f.link_hosts.length ? "ioc" : "", true));
  box.appendChild(grid);
  box.appendChild(el("p", "det-nota", "El país no se consulta. Atalaya no guarda el asunto, el cuerpo ni direcciones completas."));
  return box;
}

function actionButtons(alert) {
  const wrap = el("div", "det-botones");
  const mk = (cls, ic, label, onClick, tag) => {
    const b = el(tag || "button", "b-act " + cls);
    if (!tag) { b.type = "button"; b.addEventListener("click", onClick); }
    b.append(icon(ic), el("span", "", label));
    return b;
  };
  if (!readOnly) {
    if (alert.status !== "quarantined") {
      wrap.appendChild(mk("cuarentena", "shield-ban", "Poner en Cuarentena", (e) =>
        act(alert.id, "approve", "Correo puesto en cuarentena: salió de la bandeja y quedó guardado en la etiqueta «Sospechoso». No se borró nada.",
          alert.quarantine_needs_reason ? { title: "Poner en cuarentena", help: "Atalaya no lo marcó como riesgo alto. Explica por qué lo aíslas: queda en el informe del correo." } : null, e.currentTarget)));
    }
    if (alert.status === "quarantined" || (alert.risk !== "low" && alert.status !== "dismissed")) {
      const restoring = alert.status === "quarantined";
      wrap.appendChild(mk("legit", "circle-check", restoring ? "Sacar de Cuarentena" : "Marcar Legítimo", (e) =>
        act(alert.id, "legit", restoring ? "Sacado de cuarentena: el correo volvió a la bandeja de entrada." : "Marcado como legítimo: el correo volvió a la bandeja de entrada.",
          { title: restoring ? "Sacar de cuarentena" : "Es legítimo",
            help: restoring ? "Vas a devolver el correo a la bandeja. Explica por qué no era peligroso: queda en el informe del correo." : "Explica por qué este correo es legítimo: queda en el informe del correo." }, e.currentTarget)));
    }
    if (alert.status === "pending_approval") {
      wrap.appendChild(mk("dejar", "check", "Dejarlo donde está", (e) =>
        act(alert.id, "reject", "Se conservó la etiqueta, sin aislar el correo.",
          { title: "Dejarlo donde está", help: "Atalaya lo marcó como riesgo alto y vas a dejarlo en la bandeja. Explica por qué: queda en el informe del correo." }, e.currentTarget)));
    }
  }
  const reportUrl = "/api/alerts/" + encodeURIComponent(alert.id) + "/report";
  const view = mk("neutro", "file-search", "Ver Informe", null, "a");
  view.href = reportUrl; view.target = "_blank"; view.rel = "noopener";
  const pdf = mk("neutro", "download", "Descargar Informe", null, "a");
  pdf.href = reportUrl + "?formato=pdf&download=true"; pdf.setAttribute("download", "");
  wrap.append(view, pdf);
  return wrap;
}

function renderDetail() {
  const alert = allAlerts.find((a) => a.id === selectedId);
  if (!alert) { selectedId = null; cuerpoEl.replaceChildren(detailEmpty()); return; }
  const k = riskKey(alert);
  const top = el("div", "det-top");
  const fila = el("div", "det-fila");
  const izq = el("div", "det-izq");
  izq.appendChild(riskBadge(alert, true));
  izq.appendChild(el("span", "det-score " + k, scoreOf(alert) + " pts"));
  const chip = el("span", "estado-chip");
  chip.append(icon("clock"), document.createTextNode(statusText(alert)));
  fila.append(izq, chip);
  top.appendChild(fila);
  const head = el("div");
  const titulo = el("h2", "det-titulo", alert.sender_domain);
  titulo.id = "det-titulo";
  titulo.tabIndex = -1;
  head.appendChild(titulo);
  const part = el("div", "det-part");
  const l1 = el("div");
  const s1 = el("span");
  s1.append(document.createTextNode("De: "), el("strong", "mono", alert.sender_domain));
  l1.append(s1, el("span", "det-id", "ID " + alert.id.slice(0, 8) + " · " + formatTime(alert.received_at)));
  const l2 = el("div");
  const s2 = el("span");
  s2.append(document.createTextNode("Para: "), el("strong", "", alert.mailbox_label || accountOf(alert.mailbox_id) || "—"));
  l2.append(s2, el("span", "pill-neutro mono", alert.department));
  part.append(l1, l2);
  head.appendChild(part);
  top.appendChild(head);
  if (readOnly) {
    const ro = el("p", "det-solo-lectura");
    ro.appendChild(icon("eye"));
    ro.appendChild(el("span", "", "Rol supervisor (solo lectura): las acciones de contención están bloqueadas."));
    top.appendChild(ro);
  }
  top.appendChild(actionButtons(alert));
  if (alert.status === "quarantined") {
    top.appendChild(el("p", "det-nota", "Este correo está fuera de la bandeja, bajo la etiqueta «Sospechoso». «Sacar de Cuarentena» lo devuelve a la bandeja y te pide el motivo."));
  }

  const tabs = el("div", "det-subtabs");
  const seg = el("div", "segmentos");
  seg.setAttribute("role", "tablist");
  seg.setAttribute("aria-label", "Secciones del correo");
  const panel = el("div", "det-scroll");
  panel.setAttribute("role", "tabpanel");
  panel.id = "det-panel";
  const defs = [["forense", "Análisis Forense"], ["smtp", "Cabeceras SMTP"]];
  const fill = () => {
    panel.setAttribute("aria-labelledby", "tab-det-" + subTab);
    panel.replaceChildren(subTab === "forense" ? whyBlock(alert) : smtpBlock(alert));
    seg.querySelectorAll("[role=tab]").forEach((t) => {
      t.setAttribute("aria-selected", String(t.dataset.k === subTab));
      t.tabIndex = t.dataset.k === subTab ? 0 : -1;
    });
  };
  defs.forEach(([key, label]) => {
    const t = el("button", "sub-tab", label);
    t.type = "button";
    t.id = "tab-det-" + key;
    t.dataset.k = key;
    t.setAttribute("role", "tab");
    t.setAttribute("aria-controls", "det-panel");
    t.addEventListener("click", () => { subTab = key; fill(); });
    t.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault();
      subTab = defs.find(([x]) => x !== key)[0];
      fill();
      document.getElementById("tab-det-" + subTab).focus();
    });
    seg.appendChild(t);
  });
  tabs.appendChild(seg);
  fill();
  cuerpoEl.replaceChildren(top, fichaBlock(alert), tabs, panel);
}

// --- Motivo escrito de una decision ---------------------------------------------------------
const dlgMotivo = document.getElementById("dlg-motivo");
const motivoTexto = document.getElementById("motivo-texto");
const motivoMsg = document.getElementById("motivo-msg");
let motivoResolve = null;

function askReason(spec) {
  document.getElementById("motivo-titulo").textContent = spec.title;
  document.getElementById("motivo-ayuda").textContent = spec.help;
  motivoTexto.value = "";
  motivoMsg.textContent = "";
  dlgMotivo.showModal();
  motivoTexto.focus();
  return new Promise((resolve) => { motivoResolve = resolve; });
}

function closeReason(value) {
  dlgMotivo.close();
  if (motivoResolve) motivoResolve(value);
  motivoResolve = null;
}

document.getElementById("form-motivo").addEventListener("submit", (event) => {
  event.preventDefault();
  const text = motivoTexto.value.trim();
  if (text.length < 10) {
    motivoMsg.textContent = "Escribe el motivo con al menos 10 caracteres.";
    return;
  }
  closeReason(text);
});
document.getElementById("motivo-cancelar").addEventListener("click", () => closeReason(null));
dlgMotivo.addEventListener("cancel", () => closeReason(null));

async function act(id, verb, okMessage, reasonSpec, btn) {
  try {
    let body;
    if (reasonSpec) {
      const reason = await askReason(reasonSpec);
      if (reason === null) return; // se canceló: no se hace nada
      body = { reason };
    }
    await busy(btn, async () => {
      await api("/api/alerts/" + encodeURIComponent(id) + "/" + verb, "POST", body);
      say(okMessage, "ok");
      await load();
    });
    document.getElementById("det-titulo")?.focus(); // el boton pulsado ya no existe: el foco no se pierde
  } catch (err) {
    say(err.message, "error");
  }
}

// --- Cobertura, tarjeta de la persona y menu --------------------------------------------------
function renderCoverage(coverage) {
  const bad = coverage.filter((c) => c.status !== "connected").length;
  covEl.replaceChildren();
  covEl.classList.toggle("mal", !coverage.length || bad > 0);
  const pill = document.getElementById("cobertura-pill");
  pill.classList.toggle("mal", !coverage.length || bad > 0);
  if (!coverage.length) {
    covEl.textContent = "Sin buzones conectados";
    document.getElementById("cobertura-pill-txt").textContent = "SIN BUZONES";
  } else if (bad) {
    covEl.textContent = bad + (bad === 1 ? " buzón sin cobertura" : " buzones sin cobertura");
    document.getElementById("cobertura-pill-txt").textContent = bad + " SIN COBERTURA";
  } else {
    covEl.textContent = "● Vigilancia activa · " + coverage.length + (coverage.length === 1 ? " buzón" : " buzones");
    document.getElementById("cobertura-pill-txt").textContent = coverage.length + (coverage.length === 1 ? " BUZÓN" : " BUZONES");
  }
  const selected = filtroEl.value;
  filtroEl.replaceChildren(new Option("Todos (" + coverage.length + ")", ""));
  coverage.forEach((c) => filtroEl.appendChild(new Option(c.label, c.mailbox_id)));
  filtroEl.value = coverage.some((c) => c.mailbox_id === selected) ? selected : "";
  multiple = coverage.length > 1;
  lastCoverage = coverage;
  const keepArea = ui.area;
  areaEl.replaceChildren(new Option("Todas las áreas (" + coverage.length + ")", ""));
  AREAS.forEach((d) => {
    const n = coverage.filter((c) => c.department === d).length;
    if (n || d !== "Sin área") areaEl.appendChild(new Option(d + " (" + n + ")", d));
  });
  areaEl.value = [...areaEl.options].some((o) => o.value === keepArea) ? keepArea : "";
  ui.area = areaEl.value;
  document.getElementById("org-nombre").textContent = (mode === "demo" ? "Empresa Demo" : "Tu organización") + " · " + coverage.length + (coverage.length === 1 ? " buzón" : " buzones");
  document.getElementById("perfil-desc").textContent = coverage.length + (coverage.length === 1 ? " buzón vigilado" : " buzones vigilados");
  setBadge("n-buzones", coverage.length);
  const nAreas = new Set(coverage.map((c) => c.department).filter((d) => d !== "Sin área")).size;
  setBadge("n-analitica", nAreas ? nAreas + (nAreas === 1 ? " área" : " áreas") : 0);
}

function setBadge(id, value) {
  const b = document.getElementById(id);
  b.textContent = String(value);
  b.classList.toggle("sin-n", !value);
}

function renderPerson(who) {
  const name = mode === "demo" ? "Carlos Mendoza" : myName || "Administración";
  const initials = (mode === "demo" ? "CM" : (myName || "AD").replace(/[^A-Za-z0-9]/g, "").slice(0, 2).toUpperCase()) || "AD";
  document.getElementById("avatar").textContent = initials;
  document.getElementById("perfil-nombre").textContent = name + " · " + (readOnly ? "Supervisor" : "Administrador");
  document.getElementById("modo-txt").textContent = mode === "demo" ? "DEMO" : "";
  const perms = document.getElementById("permisos");
  perms.replaceChildren();
  const rows = readOnly
    ? [["Cuarentena:", "Bloqueado", true], ["Invitar buzones:", "Bloqueado", true], ["Informes PDF:", "Permitido", false]]
    : [["Cuarentena:", "Habilitado", false], ["Invitar buzones:", "Habilitado", false], ["Informes PDF:", "Permitido", false]];
  rows.forEach(([k, v, no]) => {
    const row = el("div");
    row.append(el("dt", "", k), el("dd", no ? "no" : "", v));
    perms.appendChild(row);
  });
  const caja = document.getElementById("rol-caja");
  const fijo = document.getElementById("rol-fijo");
  if (who.demo_roles) {
    caja.classList.remove("reserva");
    document.getElementById("rol-select").value = readOnly ? "supervisor" : "admin";
  } else {
    caja.hidden = true; // en modo conectado el rol sale del inicio de sesion, nunca de un menu
    fijo.hidden = false;
    fijo.textContent = "Rol: " + (readOnly ? "supervisor (solo lectura)" : "administración") + ", según tu inicio de sesión.";
  }
}

// --- Buzones (usuarios conectados) -------------------------------------------------------------
function timeAgo(iso) {
  if (!iso) return "sin comprobar";
  const secs = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (secs < 60) return "hace unos segundos";
  if (secs < 3600) return "hace " + Math.round(secs / 60) + " min";
  return "hace " + Math.round(secs / 3600) + " h";
}

function mailboxState(c, mine) {
  if (c.status !== "connected") return { cls: "medium", text: "Sin cobertura", rank: 3 };
  const open = mine.filter((a) => a.priority <= 1);
  if (open.some((a) => a.risk === "high")) return { cls: "high", text: "Alerta alta", rank: 2 };
  if (open.length) return { cls: "medium", text: "Alerta media", rank: 1 };
  return { cls: "ok", text: "Protegido", rank: 0 };
}

function renderMailboxes() {
  const list = document.getElementById("buzones");
  list.replaceChildren();
  const byBox = new Map();
  allAlerts.forEach((a) => { if (!byBox.has(a.mailbox_id)) byBox.set(a.mailbox_id, []); byBox.get(a.mailbox_id).push(a); });
  const st = (c) => mailboxState(c, byBox.get(c.mailbox_id) || []);
  const filters = [
    { key: "all", label: "Todos", match: () => true },
    { key: "ok", label: "Vigilados", match: (c) => c.status === "connected" },
    { key: "bad", label: "Sin cobertura", match: (c) => c.status !== "connected" },
    { key: "atencion", label: "Con alertas", match: (c) => (byBox.get(c.mailbox_id) || []).some((a) => a.priority <= 1) },
  ];
  const fbox = document.getElementById("buzones-filtros");
  fbox.replaceChildren();
  filters.forEach((f) => {
    const b = el("button", "filtro todos");
    b.type = "button";
    b.append(document.createTextNode(f.label), el("span", "n", String(lastCoverage.filter(f.match).length)));
    b.setAttribute("aria-pressed", String(ui.buzonFilter === f.key));
    b.addEventListener("click", () => { ui.buzonFilter = f.key; ui.listaLimit = PAGE; renderMailboxes(); });
    fbox.appendChild(b);
  });
  const active = filters.find((f) => f.key === ui.buzonFilter) || filters[0];
  const shown = lastCoverage
    .filter((c) => matches(c, ui.buzonQuery) && active.match(c) && (!ui.area || c.department === ui.area))
    .sort((a, b) => st(b).rank - st(a).rank || a.label.localeCompare(b.label, "es")); // lo urgente primero
  const page = shown.slice(0, ui.listaLimit);
  const more = document.getElementById("lista-mas");
  more.hidden = shown.length <= page.length;
  more.textContent = "Mostrar más (" + (shown.length - page.length) + ")";
  document.getElementById("buzones-res").textContent = "Mostrando " + page.length + " de " + lastCoverage.length + " buzones vigilados";
  page.forEach((c) => {
    const s = st(c);
    const row = el("div", "fila-tabla");
    row.setAttribute("role", "row");
    const c1 = el("span", "celda"); c1.setAttribute("role", "cell"); c1.appendChild(el("span", "celda-1", c.label));
    const ca = el("span", "celda"); ca.setAttribute("role", "cell");
    if (readOnly) {
      ca.appendChild(el("span", "celda-1", c.department));
    } else {
      const sel = el("select", "sel-area");
      sel.setAttribute("aria-label", "Área de " + c.label);
      AREAS.forEach((d) => sel.appendChild(new Option(d, d)));
      sel.value = c.department;
      sel.addEventListener("change", () => changeArea(c, sel));
      ca.appendChild(sel);
    }
    const c2 = el("span", "celda"); c2.setAttribute("role", "cell"); c2.appendChild(el("span", "celda-2", c.account));
    const c3 = el("span", "celda c-vector"); c3.setAttribute("role", "cell"); c3.appendChild(el("span", "celda-2", timeAgo(c.last_check)));
    const c4 = el("span", "celda"); c4.setAttribute("role", "cell"); c4.appendChild(el("span", "badge " + s.cls, s.text));
    const c5 = el("span", "celda acc-celda"); c5.setAttribute("role", "cell");
    const aud = button("Auditar", "btn btn-sm", () => focusMailbox(c.mailbox_id));
    aud.appendChild(icon("arrow-right"));
    aud.setAttribute("aria-label", "Auditar los correos de " + c.label);
    c5.appendChild(aud);
    if (!readOnly) c5.appendChild(button("Desconectar", "btn btn-sm btn-ghost", () => disconnect(c)));
    row.append(c1, ca, c2, c3, c4, c5);
    list.appendChild(row);
  });
  if (page.length) list.setAttribute("role", "rowgroup"); else list.removeAttribute("role");
  if (!lastCoverage.length) list.appendChild(emptyState("✉", "Todavía no hay buzones", "Cada persona conecta su correo con un enlace tuyo. Pulsa «Invitar buzón» para crear el primero."));
  else if (!page.length) list.appendChild(emptyState("⌕", "Ningún buzón coincide", "Cambia el filtro o la búsqueda."));
}

function focusMailbox(id) {
  filtroEl.value = id;
  applyFilter();
  showView("panel");
}

async function changeArea(box, sel) {
  try {
    await api("/api/mailboxes/" + encodeURIComponent(box.mailbox_id) + "/department", "PATCH", { department: sel.value });
    say("Área de " + box.label + ": " + sel.value + ".", "ok");
    await load();
  } catch (err) {
    sel.value = box.department;
    say(err.message, "error");
  }
}

async function disconnect(box) {
  if (!window.confirm("¿Desconectar " + box.label + "? Atalaya dejará de vigilar ese correo y se revocará su acceso.")) return;
  try {
    await api("/api/mailboxes/" + encodeURIComponent(box.mailbox_id), "DELETE");
    say("Buzón desconectado.", "ok");
    await load();
  } catch (err) {
    say(err.message, "error");
  }
}

const SECURITY_TEXT = {
  bloqueo: "Dirección bloqueada por demasiados intentos",
  acceso_denegado: "Una cuenta no autorizada intentó entrar",
  ataque_distribuido: "Muchos intentos fallidos desde varias direcciones",
};

async function loadSecurity() {
  const evs = await api("/api/security/events");
  const list = document.getElementById("eventos-seguridad");
  list.replaceChildren();
  evs.slice(0, 6).forEach((e) => {
    const li = el("li", "");
    li.appendChild(el("strong", "", (SECURITY_TEXT[e.kind] || e.kind) + " "));
    li.appendChild(el("span", "muted", "· " + formatDate(e.at)));
    li.appendChild(el("div", "muted", e.detail));
    list.appendChild(li);
  });
  document.getElementById("seguridad").hidden = !evs.length;
}

// --- Historial y exportacion a CSV ------------------------------------------------------------
const ACTIVITY_TEXT = {
  admin_login: "Inició sesión",
  admin_login_failed: "Intento de acceso fallido",
  admin_login_denied: "Cuenta no autorizada",
  admin_login_blocked: "Acceso bloqueado",
  invite_created: "Invitación creada",
  invite_revoked: "Invitación revocada",
  mailbox_connected: "Buzón conectado",
  mailbox_reconnected: "Buzón reconectado",
  mailbox_disconnected: "Buzón desconectado",
  mailbox_department_changed: "Cambió el área de un buzón",
  mailbox_rejected_identity: "Cuenta rechazada",
  alert_quarantine: "Cuarentena ejecutada",
  alert_kept: "Se dejó sin aislar",
  alert_legit: "Marcado legítimo",
};
const ACTIVITY_CLASS = { alert_quarantine: "high", alert_legit: "ok", alert_kept: "medium", admin_login_failed: "medium", admin_login_denied: "high", admin_login_blocked: "high", mailbox_disconnected: "medium", mailbox_rejected_identity: "high" };

function renderHistory() {
  const list = document.getElementById("historial");
  list.replaceChildren();
  events.slice(0, ui.historyLimit).forEach((e) => {
    const row = el("div", "fila-tabla");
    row.setAttribute("role", "row");
    const mk = (cls, node) => { const c = el("span", "celda" + cls); c.setAttribute("role", "cell"); c.appendChild(node); return c; };
    const when = el("span", "celda-2", formatDate(e.at));
    const bad = el("span", "badge " + (ACTIVITY_CLASS[e.action] || "estado"), ACTIVITY_TEXT[e.action] || e.action);
    row.append(mk("", when), mk("", bad), mk("", el("span", "celda-2 sans", e.detail || "—")), mk("", el("span", "celda-1", actorLabel(e.actor))));
    list.appendChild(row);
  });
  const more = document.getElementById("historial-mas");
  more.hidden = events.length <= ui.historyLimit;
  more.textContent = "Mostrar más (" + (events.length - ui.historyLimit) + ")";
  document.getElementById("historial-res").textContent = events.length ? "Mostrando " + Math.min(events.length, ui.historyLimit) + " de " + events.length + " registros" : "";
  if (events.length) list.setAttribute("role", "rowgroup"); else list.removeAttribute("role");
  setBadge("n-historial", events.length > 99 ? "99+" : events.length);
  if (!events.length) list.appendChild(emptyState("☰", "Todavía no hay actividad", "Aquí verás qué se hizo, quién y cuándo en cuanto alguien entre, invite o decida sobre un correo."));
}
document.getElementById("historial-mas").addEventListener("click", () => { ui.historyLimit += 40; renderHistory(); });

// Una celda de CSV nunca debe poder interpretarse como formula al abrirla en una hoja de calculo
function csvCell(value) {
  let t = String(value === null || value === undefined ? "" : value);
  if (/^[=+\-@\t\r]/.test(t)) t = "'" + t;
  return '"' + t.replace(/"/g, '""') + '"';
}

async function exportCsv(btn) {
  try {
    await busy(btn, async () => {
      const fresh = await api("/api/audit");
      const rows = [["tipo", "fecha", "quien", "que_paso", "detalle", "correo_id", "dominio_remitente", "motivo", "area"]];
      fresh.forEach((e) => rows.push(["actividad", e.at, actorLabel(e.actor), ACTIVITY_TEXT[e.action] || e.action, e.detail || "", "", "", "", ""]));
      allAlerts.forEach((a) => a.actions
        .filter((x) => ACTION_TEXT[x.type])
        .forEach((x) => rows.push(["decision", x.at, actorLabel(x.by), ACTION_TEXT[x.type], "", a.id, a.sender_domain, x.reason || "", a.department])));
      const csv = "﻿" + rows.map((r) => r.map(csvCell).join(",")).join("\r\n") + "\r\n";
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      const a = el("a");
      a.href = url;
      a.download = "atalaya-historial-" + new Date().toISOString().slice(0, 10) + ".csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      say("Historial exportado a CSV (" + (rows.length - 1) + " filas). No se guardó nada nuevo.", "ok");
    });
  } catch (err) {
    say(err.message, "error");
  }
}
document.getElementById("exportar-csv").addEventListener("click", (e) => exportCsv(e.currentTarget));

// --- Configuracion de auditoria (solo lectura) -------------------------------------------------
function renderPolicy() {
  const { medium, high } = policy;
  const total = Math.max(100, high + 20); // la pista muestra 0 a 100 puntos
  document.getElementById("pol-alta").textContent = high + " pts";
  document.getElementById("pol-media").textContent = medium + " pts";
  document.getElementById("pol-baja").textContent = "< " + medium + " pts";
  [["alta", high], ["media", medium]].forEach(([k, v]) => {
    document.getElementById("pista-" + k).style.setProperty("--w", (v / total) * 100 + "%");
    document.getElementById("punto-" + k).style.setProperty("--w", (v / total) * 100 + "%");
  });
  document.getElementById("kpi-alta-sub").textContent = "Score ≥ " + high;
  document.getElementById("kpi-media-sub").textContent = "Score " + medium + "–" + (high - 1);
  document.getElementById("kpi-baja-sub").textContent = "Score < " + medium;
}

// --- Analitica y trafico: todo sale de las alertas guardadas -----------------------------------
const RANGES = { "24h": { n: 24, unit: "hora" }, "7d": { n: 7, unit: "día" }, "30d": { n: 30, unit: "día" } };

function bucketsFor(range) {
  const cfg = RANGES[range];
  // En la demo el reloj es simulado: la ventana termina en el correo mas reciente.
  const latest = allAlerts.length ? Math.max(...allAlerts.map((a) => new Date(a.received_at).getTime())) : Date.now();
  const anchor = mode === "demo" ? latest : Date.now();
  let end;
  let step;
  if (cfg.unit === "hora") { step = 3600e3; end = Math.ceil(anchor / step) * step; if (end === anchor) end += step; }
  else { const d = new Date(anchor); d.setHours(24, 0, 0, 0); end = d.getTime(); step = 86400e3; }
  const start = end - cfg.n * step;
  const buckets = Array.from({ length: cfg.n }, (_, i) => ({ t: start + i * step, total: 0, high: 0, medium: 0, low: 0, safe: 0 }));
  const inRange = [];
  allAlerts.forEach((a) => {
    const t = new Date(a.received_at).getTime();
    if (t < start || t >= end) return;
    if (ui.area && a.department !== ui.area) return;
    inRange.push(a);
    const b = buckets[Math.floor((t - start) / step)];
    b.total += 1;
    b[riskKey(a)] += 1;
  });
  return { buckets, inRange, start, end, cfg };
}

function renderAnalytics() {
  if (currentView !== "analitica") return;
  const { buckets, inRange, cfg } = bucketsFor(ui.rango);
  const label = { "24h": "las últimas 24 horas", "7d": "los últimos 7 días", "30d": "los últimos 30 días" }[ui.rango];
  document.getElementById("analitica-sub").textContent = "Cifras calculadas con las alertas guardadas de " + lastCoverage.length + (lastCoverage.length === 1 ? " buzón" : " buzones") + " en " + label + ".";
  document.getElementById("grafico-sub").textContent = "Distribución " + (cfg.unit === "hora" ? "por hora" : "por día") + " en " + label +
    (mode === "demo" ? " (la ventana termina en el correo simulado más reciente)." : ".");
  document.querySelectorAll("#rango .seg").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.rango === ui.rango)));

  // Grafico de barras apiladas (limpio arriba; alta, media y baja abajo)
  const max = Math.max(1, ...buckets.map((b) => b.total));
  const chart = document.getElementById("grafico");
  const xs = document.getElementById("grafico-x");
  const tbody = document.querySelector("#grafico-tabla tbody");
  chart.replaceChildren(); xs.replaceChildren(); tbody.replaceChildren();
  const every = cfg.n === 24 ? 4 : cfg.n === 7 ? 1 : 5;
  buckets.forEach((b, i) => {
    const d = new Date(b.t);
    const name = cfg.unit === "hora" ? String(d.getHours()).padStart(2, "0") + ":00" : d.toLocaleDateString("es-PA", { day: "numeric", month: "short" });
    const col = el("div", "g-col");
    col.title = name + ": " + b.total + " analizados, " + b.high + " altas, " + b.medium + " medias, " + b.low + " bajas";
    const bar = el("div", "g-barra");
    bar.style.setProperty("--h", (b.total / max) * 100 + "%");
    [["limpio", b.safe], ["alta", b.high], ["media", b.medium], ["baja", b.low]].forEach(([k, n]) => {
      if (!n) return;
      const seg = el("div", "g-seg " + k);
      seg.style.setProperty("--h", (n / b.total) * 100 + "%");
      bar.appendChild(seg);
    });
    col.appendChild(bar);
    chart.appendChild(col);
    xs.appendChild(el("span", "", i % every === 0 ? (cfg.unit === "hora" ? name : String(d.getDate())) : ""));
    const tr = el("tr");
    [name, b.total, b.high, b.medium, b.low].forEach((v) => tr.appendChild(el("td", "", String(v))));
    tbody.appendChild(tr);
  });
  const yb = document.getElementById("grafico-y");
  yb.replaceChildren();
  [0, 1, 2, 3].forEach((i) => yb.appendChild(el("span", "", String(Math.round((max * i) / 3)))));

  // Vectores: las senales agrupadas por tipo de ataque (una alerta cuenta una vez por vector)
  const vec = new Map();
  inRange.filter((a) => a.signals.length).forEach((a) => {
    new Set(a.signals.map((s) => s.vector)).forEach((v) => {
      const e = vec.get(v) || { n: 0, worst: "low" };
      e.n += 1;
      if (a.risk === "high" || (a.risk === "medium" && e.worst === "low")) e.worst = a.risk;
      vec.set(v, e);
    });
  });
  const withSignals = inRange.filter((a) => a.signals.length).length;
  const vl = document.getElementById("vectores");
  vl.replaceChildren();
  [...vec.entries()].sort((a, b) => b[1].n - a[1].n).slice(0, 7).forEach(([name, e]) => {
    const li = el("li");
    const row = el("div", "v-fila");
    row.append(el("span", "", name), el("span", "mono", e.n + " (" + Math.round((e.n / withSignals) * 100) + "%)"));
    const track = el("div", "v-pista");
    const fillEl = el("span", e.worst);
    fillEl.style.setProperty("--w", Math.round((e.n / withSignals) * 100) + "%");
    track.appendChild(fillEl);
    li.append(row, track);
    vl.appendChild(li);
  });
  if (!vec.size) vl.appendChild(el("li", "nota", "No hay señales en este periodo."));
  document.getElementById("vectores-n").textContent = withSignals + (withSignals === 1 ? " alerta" : " alertas");
  const risky = inRange.filter((a) => a.risk !== "low").length;
  document.getElementById("tasa-riesgo").textContent = inRange.length ? ((risky / inRange.length) * 100).toFixed(1).replace(".", ",") + " %" : "—";
  document.getElementById("n-decidir").textContent = String(allAlerts.filter((a) => a.priority === 0).length);

  // Por area (no por persona: el directorio de usuarios ya es por persona)
  const areaNames = AREAS.filter((d) => lastCoverage.some((c) => c.department === d) || inRange.some((x) => x.department === d));
  const rows = areaNames.filter((d) => !ui.area || d === ui.area).map((d) => {
    const mine = inRange.filter((x) => x.department === d);
    const boxes = lastCoverage.filter((c) => c.department === d);
    const high = mine.filter((x) => x.risk === "high").length;
    const medium = mine.filter((x) => x.risk === "medium").length;
    const low = mine.filter((x) => riskKey(x) === "low").length;
    const vc = new Map();
    mine.filter((x) => x.signals.length).forEach((x) => vc.set(x.vector, (vc.get(x.vector) || 0) + 1));
    const topVec = [...vc.entries()].sort((p, q) => q[1] - p[1])[0];
    const byBox = new Map();
    mine.filter((x) => x.risk !== "low").forEach((x) => byBox.set(x.mailbox_label, (byBox.get(x.mailbox_label) || 0) + 1));
    const topBox = [...byBox.entries()].sort((p, q) => q[1] - p[1])[0];
    return { d, boxes: boxes.length, total: mine.length, high, medium, low, rate: mine.length ? (high + medium) / mine.length : 0, vector: topVec ? topVec[0] : "—", topBox };
  }).sort((p, q) => q.rate - p.rate || q.high - p.high || p.d.localeCompare(q.d, "es"));
  const pct = (r) => (r * 100).toFixed(1).replace(".", ",") + " %";
  document.getElementById("titulo-por-area-t").textContent = "Análisis detallado por área (" + rows.length + (rows.length === 1 ? " área)" : " áreas)");
  const cards = document.getElementById("area-cards");
  cards.replaceChildren();
  rows.forEach((r) => {
    const card = el("div", "b-card");
    const cab = el("div", "b-card-cab");
    const nm = el("div");
    nm.append(el("strong", "", r.d), el("div", "nota", r.boxes + (r.boxes === 1 ? " buzón" : " buzones") + " · " + r.total + (r.total === 1 ? " correo" : " correos")));
    const tasa = el("div", "b-tasa", "Tasa de riesgo");
    tasa.appendChild(el("b", r.rate >= 0.5 ? "alta" : "", pct(r.rate)));
    cab.append(nm, tasa);
    const bar = el("span", "barra-puntaje");
    const f = el("span", r.rate >= 0.5 ? "alta" : "");
    f.style.setProperty("--w", Math.round(r.rate * 100) + "%");
    bar.appendChild(f);
    const tres = el("div", "b-tres");
    [["a", "Altas", r.high], ["m", "Medias", r.medium], ["l", "Bajas", r.low]].forEach(([k, t, n]) => {
      const dd = el("div", k, t);
      dd.appendChild(el("b", "", String(n)));
      tres.appendChild(dd);
    });
    const vb = el("div", "b-vector");
    vb.append(el("span", "", "Vector principal"), document.createTextNode(r.vector));
    const ub = el("div", "b-vector");
    const uf = el("div", "b-usuario");
    const un = el("div");
    un.append(el("span", "", "Buzón más atacado"), document.createTextNode(r.topBox ? r.topBox[0] : "—"));
    uf.appendChild(un);
    if (r.topBox) uf.appendChild(el("span", "pill-neutro", r.topBox[1] + (r.topBox[1] === 1 ? " alerta" : " alertas")));
    ub.appendChild(uf);
    const go = button("Auditar área", "btn btn-sm", () => {
      areaEl.value = r.d; ui.area = r.d; filtroEl.value = "";
      applyFilter(); renderMailboxes(); showView("panel");
    });
    go.appendChild(icon("arrow-right"));
    card.append(cab, bar, tres, vb, ub, go);
    cards.appendChild(card);
  });
  const tb = document.getElementById("tabla-area");
  tb.replaceChildren();
  rows.forEach((r) => {
    const row = el("div", "fila-tabla");
    row.setAttribute("role", "row");
    const mk = (cls, ...kids) => { const c = el("span", "celda" + cls); c.setAttribute("role", "cell"); kids.forEach((k) => c.appendChild(k)); return c; };
    const rate = el("span", "tasa-celda");
    const bar = el("span", "barra-puntaje");
    const f = el("span", r.rate >= 0.5 ? "alta" : "");
    f.style.setProperty("--w", Math.round(r.rate * 100) + "%");
    bar.appendChild(f);
    rate.append(document.createTextNode(pct(r.rate)), bar);
    row.append(mk("", el("span", "celda-1", r.d)), mk(" der", el("span", "celda-2", String(r.boxes))), mk(" der", el("span", "celda-2", String(r.total))), mk(" der", el("span", "celda-2 rojo", String(r.high))),
      mk(" der", el("span", "celda-2 ambar", String(r.medium))), mk(" der", el("span", "celda-2 celeste", String(r.low))), mk("", rate), mk(" c-vector", el("span", "celda-2 sans", r.vector)));
    tb.appendChild(row);
  });
  if (rows.length) tb.setAttribute("role", "rowgroup"); else tb.removeAttribute("role");
  if (!rows.length) tb.appendChild(emptyState("✉", "Todavía no hay áreas con buzones", "Asigna un área a cada buzón en «Usuarios Conectados»."));
}
document.getElementById("rango").addEventListener("click", (e) => {
  const b = e.target.closest("[data-rango]");
  if (b) { ui.rango = b.dataset.rango; renderAnalytics(); }
});

// --- Carga de datos ---------------------------------------------------------------------------
async function load() {
  api("/api/audit").then((e) => { events = e; renderHistory(); }).catch(() => {});
  if (authRequired) loadSecurity().catch(() => {});
  // Las tres consultas salen a la vez: menos viajes de ida y vuelta antes de pintar
  const [coverage, alerts, campaigns] = await Promise.all([
    api("/api/coverage"),
    api("/api/alerts"),
    api("/api/campaigns").catch(() => []),
  ]);
  renderCoverage(coverage);
  allAlerts = alerts;
  campaignList = campaigns;
  applyFilter();
  renderMailboxes();
  renderAnalytics();
}

function applyFilter() {
  lastAlerts = allAlerts.filter((a) => (!filtroEl.value || a.mailbox_id === filtroEl.value) && (!ui.area || a.department === ui.area));
  const active = document.getElementById("filtro-activo");
  const box = lastCoverage.find((c) => c.mailbox_id === filtroEl.value);
  active.hidden = !box;
  active.replaceChildren();
  if (box) {
    active.appendChild(document.createTextNode("Viendo solo los correos de "));
    active.appendChild(el("strong", "", box.label));
    active.appendChild(document.createTextNode(". "));
    active.appendChild(button("Ver todos", "btn btn-sm btn-ghost", () => { filtroEl.value = ""; applyFilter(); }));
  }
  renderSummary();
  renderCampaigns();
  renderFilters();
  // En pantalla ancha el inspector no queda vacio: muestra el primer correo, como el prototipo
  if (wide.matches && !selectedId) { const first = visibleAlerts()[0]; if (first) selectedId = first.id; }
  renderList();
  renderDetail();
}

// --- Campanas: el mismo ataque en varios buzones ---------------------------------------------
function renderCampaigns() {
  const box = document.getElementById("campanas");
  box.replaceChildren();
  const live = campaignList.filter((c) => c.actionable > 0);
  box.classList.remove("cargando");
  box.hidden = live.length === 0;
  live.forEach((c) => {
    const card = el("div", "campana " + c.risk);
    const info = el("div", "info");
    info.appendChild(el("strong", "", "1 campaña en " + c.mailbox_count + " buzones"));
    info.appendChild(el("span", "muted mono", " · " + c.sender_domain));
    info.appendChild(el("div", "muted", c.mailboxes.join(", ")));
    card.appendChild(info);
    const n = c.actionable;
    const label = n === c.mailbox_count ? "Poner en cuarentena en los " + n + " buzones" : "Poner en cuarentena los " + n + " restantes";
    if (!readOnly) card.appendChild(button(label, c.pending ? "btn btn-main" : "btn", (e) =>
      actCampaign(c, "Cuarentena aplicada a " + n + " correos de la campaña. Nada se borró: puedes sacarlos de cuarentena uno por uno.", e.currentTarget)));
    box.appendChild(card);
  });
}

async function actCampaign(c, okMessage, btn) {
  try {
    let body;
    if (c.needs_reason) {
      const reason = await askReason({
        title: "Cuarentena en " + c.actionable + " buzones",
        help: "Algunos de estos correos no estaban marcados como riesgo alto. Explica por qué los aíslas todos: el motivo queda en el informe de cada correo.",
      });
      if (reason === null) return;
      body = { reason };
    }
    const res = await busy(btn, () => api("/api/campaigns/" + encodeURIComponent(c.id) + "/quarantine", "POST", body));
    say(res.failed ? okMessage + " " + res.failed + " no se pudieron aislar." : okMessage, res.failed ? "error" : "ok");
    tourDone(2);
    await load();
  } catch (err) {
    say(err.message, "error");
  }
}

// --- Cifras del panel --------------------------------------------------------------------------
function showLoadError(err) {
  listaEl.replaceChildren(emptyState("!", "No pudimos cargar el panel", (err && err.message ? err.message + " " : "") + "Comprueba tu conexión e inténtalo otra vez.",
    button("Reintentar", "btn btn-main", () => { load().then(() => say("Listo: el panel se cargó.", "ok")).catch(showLoadError); })));
}

function renderSummary() {
  const decide = allAlerts.filter((a) => a.priority === 0).length;
  const review = allAlerts.filter((a) => a.priority === 1).length;
  // Texto para lectores de pantalla: lo mas importante primero
  document.getElementById("estado-titulo").textContent = decide
    ? decide + (decide === 1 ? " correo requiere" : " correos requieren") + " tu decisión. "
    : review ? review + (review === 1 ? " correo para revisar. " : " correos para revisar. ") : "Todo en orden. ";
  document.getElementById("estado-detalle").textContent = "Atalaya no aísla ni borra nada sin tu aprobación.";
  setBadge("n-correos", decide);
  // Cifras reales: conteos de las alertas que Atalaya guarda
  const lim = lastAlerts;
  document.getElementById("kpi-total").textContent = String(lim.length);
  document.getElementById("kpi-total-sub").textContent = lastCoverage.length + (lastCoverage.length === 1 ? " buzón" : " buzones");
  document.getElementById("kpi-alta").textContent = String(lim.filter(FILTERS.find((f) => f.key === "high").match).length);
  document.getElementById("kpi-media").textContent = String(lim.filter(FILTERS.find((f) => f.key === "medium").match).length);
  document.getElementById("kpi-baja").textContent = String(lim.filter(FILTERS.find((f) => f.key === "low").match).length);
}

// --- Invitaciones --------------------------------------------------------------------------
const dlg = document.getElementById("dlg-invitar");
const invLabel = document.getElementById("inv-label");
const invUrl = document.getElementById("inv-url");
const invRes = document.getElementById("inv-resultado");
const invMsg = document.getElementById("inv-msg");
const invList = document.getElementById("inv-lista");

async function loadInvites() {
  const invites = await api("/api/invites");
  invList.replaceChildren();
  invites.slice(0, 8).forEach((i) => {
    const li = el("li", "");
    const info = el("div", "");
    info.appendChild(el("strong", "", i.label));
    info.appendChild(el("span", "muted", " · " + (i.department || "Sin área") + " · " + INVITE_TEXT[i.status] + " · vence " + formatDate(i.expires_at)));
    li.appendChild(info);
    if (i.status === "pending") {
      li.appendChild(button("Revocar", "btn btn-sm btn-ghost", async () => {
        try { await api("/api/invites/" + encodeURIComponent(i.id) + "/revoke", "POST"); await loadInvites(); }
        catch (err) { invMsg.textContent = err.message; }
      }));
    }
    invList.appendChild(li);
  });
  if (!invites.length) invList.appendChild(el("li", "muted", "Aún no hay invitaciones. Escribe un nombre arriba y pulsa «Crear enlace»."));
}

const invArea = document.getElementById("inv-area");
AREAS.forEach((d) => invArea.appendChild(new Option(d, d)));
invArea.value = "Sin área";

document.getElementById("btn-invitar").addEventListener("click", async () => {
  invRes.hidden = true;
  invMsg.textContent = "";
  invLabel.value = "";
  dlg.showModal();
  invLabel.focus();
  loadInvites().catch((err) => { invMsg.textContent = err.message; });
});

document.getElementById("form-invitar").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const created = await api("/api/invites", "POST", { label: invLabel.value, department: invArea.value });
    invUrl.value = created.url;
    invRes.hidden = false;
    invMsg.textContent = "Enlace creado. Cópialo y envíaselo a la persona: solo funciona una vez.";
    invUrl.select();
    await loadInvites();
  } catch (err) {
    invMsg.textContent = err.message;
  }
});

document.getElementById("inv-copiar").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(invUrl.value);
    invMsg.textContent = "Enlace copiado.";
  } catch {
    invUrl.select();
    invMsg.textContent = "Selecciona el enlace y cópialo con Ctrl + C.";
  }
});

document.getElementById("inv-cerrar").addEventListener("click", async () => {
  invUrl.value = "";
  dlg.close();
  await load().catch(() => {});
});

// --- Guia de primera visita (demo): 3 pasos, se puede cerrar y volver a abrir ---------------
const TOUR_KEY = "atalaya-guia";
const TOUR_STEPS = [
  { title: "Mira la campaña", text: "El mismo correo falso llegó a varios buzones a la vez. Atalaya lo detecta y lo agrupa en una sola alerta.", cta: "Ver la campaña",
    go: () => { showView("panel"); const c = document.getElementById("campanas"); (c.hidden ? listaEl : c).scrollIntoView({ block: "center" }); } },
  { title: "Aíslala con tu aprobación", text: "Pulsa el botón de la campaña para poner todos esos correos en cuarentena. Nada se borra y puedes deshacerlo.", cta: "Ir al botón",
    go: () => { showView("panel"); const b = document.querySelector("#campanas .btn"); if (b) { b.scrollIntoView({ block: "center" }); b.focus(); } else say("No hay campañas activas. Usa «Reiniciar demostración» para verla otra vez."); } },
  { title: "Cambia a supervisor", text: "Mira cómo se ve el panel para alguien que solo puede leer: no puede aprobar ni invitar.", cta: "Ver como supervisor",
    go: () => { if (!wide.matches || window.innerWidth < 800) setMenu(true, false); const b = document.getElementById("rol-select"); if (b && !document.getElementById("rol-caja").hidden) b.focus(); } },
];
function loadTour() {
  try { return Object.assign({ done: [], closed: false }, JSON.parse(localStorage.getItem(TOUR_KEY) || "{}")); }
  catch { return { done: [], closed: false }; }
}
function saveTour(t) { try { localStorage.setItem(TOUR_KEY, JSON.stringify(t)); } catch { /* sin almacenamiento */ } }
function tourDone(step) {
  const t = loadTour();
  if (!t.done.includes(step)) { t.done.push(step); saveTour(t); }
  if (!document.getElementById("guia").hidden) drawTour();
}
function drawTour() {
  const t = loadTour();
  const current = TOUR_STEPS.findIndex((_, i) => !t.done.includes(i + 1));
  const box = document.getElementById("guia");
  if (current === -1) { box.hidden = true; return; }
  const step = TOUR_STEPS[current];
  document.getElementById("guia-paso").textContent = "Paso " + (current + 1) + " de " + TOUR_STEPS.length;
  document.getElementById("guia-titulo").textContent = step.title;
  document.getElementById("guia-texto").textContent = step.text;
  const hacer = document.getElementById("guia-hacer");
  hacer.textContent = step.cta;
  hacer.onclick = () => { step.go(); if (current === 0) tourDone(1); };
  const dots = document.getElementById("guia-puntos");
  dots.replaceChildren();
  TOUR_STEPS.forEach((_, i) => dots.appendChild(el("span", "puntito" + (t.done.includes(i + 1) ? " hecho" : i === current ? " actual" : ""))));
  box.hidden = false;
}
function startTour(enabled) {
  const open = document.getElementById("guia-abrir"); // no existe en modo conectado
  if (open) open.hidden = !enabled;
  if (!enabled) return;
  if (!loadTour().closed) drawTour();
}
document.getElementById("guia-cerrar").addEventListener("click", () => {
  const t = loadTour(); t.closed = true; saveTour(t);
  document.getElementById("guia").hidden = true;
  const open = document.getElementById("guia-abrir");
  if (open) open.focus();
});
document.getElementById("guia-abrir").addEventListener("click", () => {
  const t = loadTour(); t.closed = false;
  if (t.done.length >= TOUR_STEPS.length) t.done = [];
  saveTour(t); drawTour();
  document.getElementById("guia-hacer").focus();
});
document.getElementById("guia").addEventListener("keydown", (e) => {
  if (e.key === "Escape") document.getElementById("guia-cerrar").click();
});

// --- Arranque ------------------------------------------------------------------------------
filtroEl.addEventListener("change", () => { ui.limit = 40; applyFilter(); });
areaEl.addEventListener("change", () => { ui.area = areaEl.value; ui.limit = 40; ui.listaLimit = PAGE; applyFilter(); renderMailboxes(); });
document.getElementById("buscar-lista").addEventListener("input", (e) => { ui.buzonQuery = e.target.value.trim(); ui.listaLimit = PAGE; renderMailboxes(); });
document.getElementById("lista-mas").addEventListener("click", () => { ui.listaLimit += PAGE; renderMailboxes(); });
window.addEventListener("hashchange", () => showView(window.location.hash.slice(1)));

document.getElementById("reset").addEventListener("click", async () => {
  try {
    await api("/api/demo/reset", "POST");
    say("Demostración reiniciada: los correos volvieron a su estado inicial.", "ok");
    await load();
  } catch (err) {
    say(err.message, "error");
  }
});

document.getElementById("btn-salir").addEventListener("click", async () => {
  await fetch("/auth/admin/logout", { method: "POST", headers: { "X-Requested-With": "atalaya" } });
  window.location.href = "/login";
});

async function init() {
  showView(window.location.hash.slice(1));
  listaEl.setAttribute("aria-busy", "true");
  for (let i = 0; i < 5; i++) { const sk = el("div", "esqueleto"); sk.setAttribute("aria-hidden", "true"); listaEl.appendChild(sk); }
  cuerpoEl.replaceChildren(detailEmpty());
  // Salud y rol se piden a la vez (la demo crea la copia del visitante con la primera respuesta)
  const [healthRes, who0] = await Promise.all([fetch("/health"), api("/api/whoami").catch(() => null)]);
  const health = await healthRes.json();
  mode = health.mode;
  authRequired = health.auth;
  if (mode === "gmail") {
    document.getElementById("reset").hidden = true;
    document.getElementById("banner").textContent =
      "Modo conectado: solo para uso local con cuentas de prueba.";
    setInterval(() => load().catch(() => {}), 30000);
  }
  if (authRequired) {
    document.getElementById("btn-salir").hidden = false;
    api("/api/me").then((me) => { myName = me.id; renderPerson(whoCache); }).catch(() => {});
  }
  api("/api/policy").then((p) => { policy = p; renderPolicy(); }).catch(() => renderPolicy());
  const who = who0 || { role: "admin", demo_roles: false };
  whoCache = who;
  readOnly = who.role === "supervisor";
  if (readOnly) {
    document.getElementById("banner-rol").hidden = false;
    ["btn-invitar", "reset"].forEach((id) => { document.getElementById(id).hidden = true; });
  }
  renderPerson(who);
  if (who.demo_roles) {
    document.getElementById("rol-select").addEventListener("change", async (e) => {
      try {
        await api("/api/demo/role", "POST", { role: e.target.value });
        if (e.target.value === "supervisor") tourDone(3);
        window.location.reload();
      } catch (err) {
        say(err.message, "error");
      }
    });
  }
  startTour(mode === "demo" && !readOnly && !!who.demo_roles);
  await load();
}
let whoCache = { role: "admin", demo_roles: false };

init().catch((err) => { showLoadError(err); });

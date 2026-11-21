// Panel de Atalaya (administracion). Todo contenido dinamico se inserta con
// textContent o nodos creados a mano (nunca innerHTML), asi que el texto de un correo
// no puede ejecutar codigo. Los anchos de las barras se asignan con style.setProperty.
"use strict";

const RISK_TEXT = { high: "Riesgo alto", medium: "Riesgo medio", low: "Riesgo bajo" };
const STATUS_TEXT = {
  new: "Nuevo",
  labeled: "Etiquetado",
  pending_approval: "Esperando tu decisión",
  quarantined: "En cuarentena",
  dismissed: "Sin acción",
};
const ACTION_TEXT = {
  quarantine: "Puso el correo en cuarentena",
  reject_quarantine: "Decidió no aislarlo y dejarlo donde estaba",
  mark_legit: "Lo devolvió a la bandeja como legítimo",
};
const REVIEW_OUTCOME = {
  mark_legit: "Revisado: era legítimo",
  reject_quarantine: "Revisado: se dejó sin aislar",
};
const INVITE_TEXT = { pending: "Pendiente", used: "Usada", expired: "Vencida", revoked: "Revocada" };
const VIEWS = {
  panel: "Panel de control",
  buzones: "Buzones",
  historial: "Historial",
  politica: "Cómo se calcula el riesgo",
};
const OLD_HASHES = { correos: "panel", resumen: "panel" }; // enlaces de la version anterior

const lastHuman = (a) => {
  const h = a.actions.filter((x) => REVIEW_OUTCOME[x.type]);
  return h.length ? h[h.length - 1].type : null;
};
const FILTERS = [
  { key: "all", label: "Todos", cls: "", match: () => true },
  { key: "high", label: "Alta", cls: "alta", match: (a) => a.risk === "high" },
  { key: "medium", label: "Media", cls: "media", match: (a) => a.risk === "medium" },
  { key: "low", label: "Baja", cls: "baja", match: (a) => a.risk === "low" },
  { key: "quarantine", label: "Cuarentena", cls: "", match: (a) => a.status === "quarantined" },
  { key: "legit", label: "Legítimos", cls: "legit", match: (a) => lastHuman(a) === "mark_legit" },
];

// --- Estado de la vista (solo del navegador; no son datos de correos) ---
let allAlerts = [];
let lastAlerts = []; // con el filtro de buzon
let campaignList = [];
let lastCoverage = [];
let events = [];
let policy = { medium: 30, high: 60 };
let selectedId = null;
let detTab = "analisis";
let currentView = "panel";
const PAGE = 24;
const ui = { filter: "all", query: "", limit: 40, listaLimit: PAGE, historyLimit: 40 };
const norm = (t) => t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const matches = (c, q) => !q || norm(c.label + " " + c.account).includes(norm(q));
const scoreOf = (a) => a.signals.reduce((n, s) => n + s.weight, 0);

const msgEl = document.getElementById("mensaje");
const covEl = document.getElementById("coverage");
const filtroEl = document.getElementById("filtro");
const listaEl = document.getElementById("lista-correos");
const detalleEl = document.getElementById("detalle");
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

function linkButton(label, href, cls, download) {
  const a = el("a", cls, label);
  a.href = href;
  if (download) a.setAttribute("download", "");
  else { a.target = "_blank"; a.rel = "noopener"; }
  return a;
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

// Estado vacio o de error: explica que pasa y, si se puede, ofrece una salida
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

function statusText(alert) {
  if (alert.status === "quarantined") return "En cuarentena";
  if (alert.reviewed) {
    const human = lastHuman(alert);
    if (human) return REVIEW_OUTCOME[human];
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
  if (actor === "admin-demo") return "Administración (demo)";
  return actor;
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
    b.append(document.createTextNode(f.label + " "), el("span", "n", String(n)));
    b.setAttribute("aria-pressed", String(ui.filter === f.key));
    b.addEventListener("click", () => { ui.filter = f.key; ui.limit = 40; renderList(); renderFilters(); });
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

function renderRow(a) {
  const li = el("li", "fila-correo " + a.risk);
  const b = el("button", "fila-btn");
  b.type = "button";
  if (a.id === selectedId) b.setAttribute("aria-current", "true");
  const quien = el("span", "fila-quien");
  quien.appendChild(el("span", "fila-dom", a.sender_domain));
  quien.appendChild(el("span", "fila-meta", formatDate(a.received_at) + (a.mailbox_label ? " · " + a.mailbox_label : "")));
  const badges = el("span", "fila-badges");
  badges.appendChild(el("span", "badge " + a.risk, RISK_TEXT[a.risk]));
  badges.appendChild(el("span", a.status === "pending_approval" ? "badge decidir" : "badge estado", statusText(a)));
  const bar = el("span", "barra-puntaje");
  const fill = el("span");
  fill.style.setProperty("--w", Math.min(100, scoreOf(a)) + "%");
  bar.appendChild(fill);
  b.append(quien, badges, bar, el("span", "fila-puntaje", scoreOf(a) + " pts"));
  b.addEventListener("click", (e) => openDetail(a.id, e.currentTarget));
  li.appendChild(b);
  return li;
}

function renderList() {
  const items = visibleAlerts();
  const shown = items.slice(0, ui.limit);
  const nodes = shown.map(renderRow);
  listaEl.replaceChildren(...nodes);
  listaEl.removeAttribute("aria-busy");
  const more = document.getElementById("correos-mas");
  more.hidden = items.length <= shown.length;
  more.textContent = "Mostrar más (" + (items.length - shown.length) + " restantes)";
  document.getElementById("lista-resumen").textContent =
    items.length ? "Mostrando " + shown.length + " de " + items.length + (items.length === 1 ? " correo." : " correos.") : "";
  if (!lastAlerts.length) {
    listaEl.appendChild(emptyState("✓", "Bandeja tranquila", filtroEl.value
      ? "Este buzón no tiene correos por revisar."
      : "Atalaya aún no ha marcado ningún correo. Cuando llegue uno sospechoso, aparecerá aquí con su explicación."));
  } else if (!items.length) {
    listaEl.appendChild(emptyState("⌕", "Ningún correo coincide", "Cambia el filtro o la búsqueda.",
      button("Quitar filtros", "btn", () => { ui.filter = "all"; ui.query = ""; document.getElementById("buscar-correos").value = ""; renderFilters(); renderList(); })));
  }
}
document.getElementById("buscar-correos").addEventListener("input", (e) => { ui.query = e.target.value; ui.limit = 40; renderList(); });
document.getElementById("correos-mas").addEventListener("click", () => { ui.limit += 40; renderList(); });

// --- Detalle del correo --------------------------------------------------------------------
function detailEmpty() {
  const box = el("div", "det-vacio");
  box.appendChild(icon("shield-check"));
  box.appendChild(el("strong", "", "Elige un correo de la lista"));
  box.appendChild(el("p", "", "Aquí verás por qué Atalaya desconfía de él y qué puedes hacer."));
  return box;
}

const AUTH_CODES = { SPF: "spf_fail", DKIM: "dkim_fail", DMARC: "dmarc_fail" };
const SOURCE_TEXT = { ai: "Resumen con IA", simulated: "Resumen simulado (sin IA real)", rules: "Reglas de Atalaya" };

function whyBlock(alert) {
  const frag = document.createDocumentFragment();
  frag.appendChild(el("h3", "det-h", "¿Por qué Atalaya detectó esta amenaza?"));
  if (alert.explanation_source !== "rules") {
    const resumen = el("p", "resumen-ia");
    resumen.appendChild(el("span", "tag", SOURCE_TEXT[alert.explanation_source] || "Resumen"));
    resumen.appendChild(document.createTextNode(alert.explanation.replace(/^Resumen simulado:\s*/, "")));
    frag.appendChild(resumen);
  }
  if (!alert.signals.length) {
    frag.appendChild(el("p", "nota", "Atalaya no encontró nada sospechoso en este correo."));
    return frag;
  }
  const ol = el("ol", "por-que");
  alert.signals.slice().sort((a, b) => b.weight - a.weight).forEach((s) => {
    const li = el("li", "", s.description);
    li.appendChild(el("span", "peso", "+" + s.weight + " puntos"));
    ol.appendChild(li);
  });
  frag.appendChild(ol);
  frag.appendChild(el("p", "nota", "Los hechos (verificaciones SPF, DKIM, DMARC, dominios parecidos, enlaces) los calcula el código de Atalaya. La IA solo redacta el resumen."));
  return frag;
}

function timelineBlock(alert) {
  const frag = document.createDocumentFragment();
  if (!alert.actions.length) return frag;
  frag.appendChild(el("h3", "det-h", "Qué pasó con este correo"));
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
  return frag;
}

function techBlock(alert) {
  const frag = document.createDocumentFragment();
  const box = lastCoverage.find((c) => c.mailbox_id === alert.mailbox_id);
  const dl = el("dl", "ficha");
  const row = (k, v) => {
    dl.appendChild(el("dt", "", k));
    const dd = el("dd", "");
    if (v instanceof Node) dd.appendChild(v); else dd.textContent = v;
    dl.appendChild(dd);
  };
  row("Dominio del remitente", alert.sender_domain);
  row("Buzón", box ? box.account : alert.mailbox_label || alert.mailbox_id);
  row("Recibido", formatDate(alert.received_at));
  row("Identificador", alert.message_ref);
  row("Puntaje", scoreOf(alert) + " pts · " + RISK_TEXT[alert.risk]);
  row("Estado", statusText(alert));
  row("Explicación", SOURCE_TEXT[alert.explanation_source] || alert.explanation_source);
  const auth = el("span", "");
  Object.entries(AUTH_CODES).forEach(([name, code]) => {
    const failed = alert.signals.some((s) => s.code === code);
    auth.appendChild(el("span", "chip-auth " + (failed ? "falla" : "bien"), name + (failed ? " falló" : " sin alerta")));
    auth.appendChild(document.createTextNode(" "));
  });
  row("Autenticación", auth);
  frag.appendChild(dl);
  if (alert.signals.length) {
    frag.appendChild(el("h3", "det-h", "Señales (código · puntos)"));
    const ul = el("ul", "linea");
    alert.signals.forEach((s) => {
      const li = el("li", "");
      li.appendChild(el("span", "mono", s.code));
      li.appendChild(document.createTextNode(" · " + s.weight + " pts"));
      ul.appendChild(li);
    });
    frag.appendChild(ul);
  }
  frag.appendChild(el("p", "nota", "Atalaya no guarda el asunto, el cuerpo, los enlaces ni los adjuntos: solo estos datos."));
  return frag;
}

function actionButtons(alert) {
  const actions = el("div", "det-acciones");
  if (readOnly) return actions;
  if (alert.status !== "quarantined") {
    actions.appendChild(button("Poner en cuarentena", alert.status === "pending_approval" ? "btn btn-main" : "btn", (e) =>
      act(alert.id, "approve", "Correo puesto en cuarentena: salió de la bandeja y quedó guardado en la etiqueta «Sospechoso». No se borró nada.",
        alert.quarantine_needs_reason ? { title: "Poner en cuarentena", help: "Atalaya no lo marcó como riesgo alto. Explica por qué lo aíslas: queda en el informe del correo." } : null, e.currentTarget)));
  }
  if (alert.status === "pending_approval") {
    actions.appendChild(button("Dejarlo donde está", "btn", (e) =>
      act(alert.id, "reject", "Se conservó la etiqueta, sin aislar el correo.",
        { title: "Dejarlo donde está", help: "Atalaya lo marcó como riesgo alto y vas a dejarlo en la bandeja. Explica por qué: queda en el informe del correo." }, e.currentTarget)));
  }
  if (alert.status === "quarantined" || (alert.risk !== "low" && alert.status !== "dismissed")) {
    const restoring = alert.status === "quarantined";
    actions.appendChild(button(restoring ? "Sacar de cuarentena" : "Es legítimo", "btn btn-ok", (e) =>
      act(alert.id, "legit", restoring ? "Sacado de cuarentena: el correo volvió a la bandeja de entrada." : "Marcado como legítimo: el correo volvió a la bandeja de entrada.",
        { title: restoring ? "Sacar de cuarentena" : "Es legítimo",
          help: restoring ? "Vas a devolver el correo a la bandeja. Explica por qué no era peligroso: queda en el informe del correo." : "Explica por qué este correo es legítimo: queda en el informe del correo." }, e.currentTarget)));
  }
  return actions;
}

function renderDetail() {
  const alert = allAlerts.find((a) => a.id === selectedId);
  if (!alert) { selectedId = null; cuerpoEl.replaceChildren(detailEmpty()); return; }
  const nodes = [];
  const cab = el("div", "det-cab");
  cab.appendChild(el("span", "badge " + alert.risk, RISK_TEXT[alert.risk]));
  cab.appendChild(el("span", alert.status === "pending_approval" ? "badge decidir" : "badge estado", statusText(alert)));
  cab.appendChild(el("span", "det-puntaje", "Puntaje " + scoreOf(alert) + " pts"));
  nodes.push(cab);
  const titulo = el("h2", "det-titulo", alert.sender_domain);
  titulo.id = "det-titulo";
  titulo.tabIndex = -1;
  nodes.push(titulo);
  nodes.push(el("p", "det-sub", formatDate(alert.received_at) + (alert.mailbox_label ? " · " + alert.mailbox_label : "")));
  if (readOnly) {
    const ro = el("p", "det-solo-lectura");
    ro.appendChild(icon("eye"));
    ro.appendChild(el("span", "", "Solo lectura: puedes ver el informe, pero no decidir."));
    nodes.push(ro);
  }
  nodes.push(actionButtons(alert));
  if (alert.status === "quarantined") {
    nodes.push(el("p", "nota", "Este correo está fuera de la bandeja, bajo la etiqueta «Sospechoso». «Sacar de cuarentena» lo devuelve a la bandeja y te pide el motivo."));
  }
  const reportUrl = "/api/alerts/" + encodeURIComponent(alert.id) + "/report";
  const informes = el("div", "det-informes");
  informes.appendChild(linkButton("Ver informe", reportUrl, "btn btn-ghost", false));
  informes.appendChild(linkButton("Descargar PDF", reportUrl + "?formato=pdf&download=true", "btn btn-ghost", true));
  informes.appendChild(linkButton("Descargar texto", reportUrl + "?download=true", "btn btn-ghost", true));
  nodes.push(informes);

  // Pestanas del detalle: lo sencillo primero; el detalle tecnico, detras de una pestana
  const tabs = el("div", "tabs-det");
  tabs.setAttribute("role", "tablist");
  tabs.setAttribute("aria-label", "Secciones del correo");
  const panel = el("div", "det-panel");
  panel.setAttribute("role", "tabpanel");
  panel.id = "det-panel";
  const tabDefs = [["analisis", "Análisis"], ["ficha", "Ficha técnica"]];
  const fill = () => {
    panel.setAttribute("aria-labelledby", "tab-det-" + detTab);
    panel.replaceChildren(...(detTab === "analisis" ? [whyBlock(alert), timelineBlock(alert)] : [techBlock(alert)]));
  };
  tabDefs.forEach(([key, label]) => {
    const t = el("button", "tab-det", label);
    t.type = "button";
    t.id = "tab-det-" + key;
    t.setAttribute("role", "tab");
    t.setAttribute("aria-controls", "det-panel");
    const sync = () => { t.setAttribute("aria-selected", String(detTab === key)); t.tabIndex = detTab === key ? 0 : -1; };
    sync();
    t.addEventListener("click", () => { detTab = key; tabs.querySelectorAll("[role=tab]").forEach((x) => x.dispatchEvent(new Event("sync"))); fill(); });
    t.addEventListener("sync", sync);
    t.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      e.preventDefault();
      const other = tabDefs.find(([k]) => k !== key)[0];
      document.getElementById("tab-det-" + other).click();
      document.getElementById("tab-det-" + other).focus();
    });
    tabs.appendChild(t);
  });
  fill();
  nodes.push(tabs, panel);
  cuerpoEl.replaceChildren(...nodes);
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

// --- Buzones -------------------------------------------------------------------------------
function renderCoverage(coverage) {
  covEl.replaceChildren();
  const bad = coverage.filter((c) => c.status !== "connected").length;
  if (!coverage.length) {
    covEl.appendChild(el("span", "bad", "● Sin buzones conectados"));
  } else if (bad) {
    covEl.appendChild(el("span", "bad", "● " + bad + (bad === 1 ? " buzón sin cobertura" : " buzones sin cobertura")));
  } else {
    covEl.appendChild(el("span", "ok", "● Vigilando " + coverage.length + (coverage.length === 1 ? " buzón" : " buzones")));
  }
  // filtro de buzon: conserva la seleccion
  const selected = filtroEl.value;
  filtroEl.replaceChildren(new Option("Todos los buzones", ""));
  coverage.forEach((c) => filtroEl.appendChild(new Option(c.label, c.mailbox_id)));
  filtroEl.value = coverage.some((c) => c.mailbox_id === selected) ? selected : "";
  multiple = coverage.length > 1;
  lastCoverage = coverage;
}

function timeAgo(iso) {
  if (!iso) return "sin comprobar";
  const secs = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (secs < 60) return "hace unos segundos";
  if (secs < 3600) return "hace " + Math.round(secs / 60) + " min";
  return "hace " + Math.round(secs / 3600) + " h";
}

function renderMailboxes() {
  const list = document.getElementById("buzones");
  list.replaceChildren();
  const q = document.getElementById("buscar-lista").value.trim();
  const onlyAttention = document.getElementById("solo-atencion").checked;
  document.getElementById("buzones-buscar").hidden = lastCoverage.length < 8;
  const byBox = new Map();
  allAlerts.forEach((a) => { if (!byBox.has(a.mailbox_id)) byBox.set(a.mailbox_id, []); byBox.get(a.mailbox_id).push(a); });
  const pending = (c) => (byBox.get(c.mailbox_id) || []).filter((a) => a.priority <= 1).length;
  const need = (c) => pending(c) + (c.status !== "connected" ? 1000 : 0);
  const shown = lastCoverage
    .filter((c) => matches(c, q) && (!onlyAttention || need(c) > 0))
    .sort((a, b) => need(b) - need(a) || a.label.localeCompare(b.label, "es")); // lo urgente primero
  const page = shown.slice(0, ui.listaLimit);
  const more = document.getElementById("lista-mas");
  more.hidden = shown.length <= page.length;
  more.textContent = "Mostrar más (" + (shown.length - page.length) + " restantes)";
  const note = document.getElementById("lista-mas-nota");
  note.hidden = lastCoverage.length <= PAGE;
  note.textContent = "Mostrando " + page.length + " de " + lastCoverage.length + " buzones, los que necesitan atención primero.";
  page.forEach((c) => {
    const ok = c.status === "connected";
    const mine = byBox.get(c.mailbox_id) || [];
    const decide = mine.filter((a) => a.priority === 0).length;
    const review = mine.filter((a) => a.priority === 1).length;
    const li = el("li", "buzon" + (ok ? "" : " sin-cobertura"));
    const info = el("div", "info");
    info.appendChild(el("strong", "", c.label));
    info.appendChild(el("span", "cuenta", c.account));
    const counts = el("div", "cuentas");
    if (decide) counts.appendChild(el("span", "urgente", decide + (decide === 1 ? " por decidir" : " por decidir")));
    if (review) counts.appendChild(el("span", "", review + " para revisar"));
    if (!decide && !review) counts.appendChild(el("span", "", mine.length ? "Sin correos pendientes" : "Sin correos todavía"));
    counts.appendChild(el("span", "", "Último chequeo: " + timeAgo(c.last_check)));
    info.appendChild(counts);
    li.appendChild(info);
    const acc = el("div", "acciones");
    acc.appendChild(el("span", "badge " + (ok ? "ok" : "medium"), ok ? "Vigilado" : "Sin cobertura"));
    acc.appendChild(button("Ver sus correos", "btn btn-ghost", () => focusMailbox(c.mailbox_id)));
    if (!readOnly) acc.appendChild(button("Desconectar", "btn btn-ghost", () => disconnect(c)));
    li.appendChild(acc);
    list.appendChild(li);
  });
  if (!lastCoverage.length) list.appendChild(emptyState("✉", "Todavía no hay buzones", "Cada persona conecta su correo con un enlace tuyo. Pulsa «Invitar buzón» para crear el primero."));
  else if (!page.length) list.appendChild(emptyState("⌕", "Ningún buzón coincide", "Cambia la búsqueda o quita el filtro «solo los que necesitan atención»."));
}

function focusMailbox(id) {
  filtroEl.value = id;
  applyFilter();
  showView("panel");
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
  admin_login_denied: "Una cuenta no autorizada intentó entrar",
  admin_login_blocked: "Acceso bloqueado por demasiados intentos",
  invite_created: "Creó una invitación",
  invite_revoked: "Revocó una invitación",
  mailbox_connected: "Se conectó un buzón",
  mailbox_reconnected: "Se reconectó un buzón",
  mailbox_disconnected: "Se desconectó un buzón",
  mailbox_rejected_identity: "Se rechazó una cuenta con caracteres sospechosos",
  alert_quarantine: "Puso un correo en cuarentena",
  alert_kept: "Decidió no aislar un correo",
  alert_legit: "Sacó un correo de cuarentena o lo marcó como legítimo",
};

function renderHistory() {
  const list = document.getElementById("historial");
  list.replaceChildren();
  events.slice(0, ui.historyLimit).forEach((e) => {
    const li = el("li", "evento");
    li.appendChild(el("span", "muted hora-ev", formatDate(e.at)));
    li.appendChild(el("strong", "", ACTIVITY_TEXT[e.action] || e.action));
    li.appendChild(el("span", "muted", " · " + actorLabel(e.actor) + (e.detail ? " · " + e.detail : "")));
    list.appendChild(li);
  });
  const more = document.getElementById("historial-mas");
  more.hidden = events.length <= ui.historyLimit;
  more.textContent = "Mostrar más (" + (events.length - ui.historyLimit) + " restantes)";
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
      const rows = [["tipo", "fecha", "quien", "que_paso", "detalle", "correo_id", "dominio_remitente", "motivo"]];
      fresh.forEach((e) => rows.push(["actividad", e.at, actorLabel(e.actor), ACTIVITY_TEXT[e.action] || e.action, e.detail || "", "", "", ""]));
      allAlerts.forEach((a) => a.actions
        .filter((x) => ACTION_TEXT[x.type])
        .forEach((x) => rows.push(["decision", x.at, actorLabel(x.by), ACTION_TEXT[x.type], "", a.id, a.sender_domain, x.reason || ""])));
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

// --- Como se calcula el riesgo (solo lectura) -------------------------------------------------
function renderPolicy() {
  const { medium, high } = policy;
  document.getElementById("pol-alta").textContent = "≥ " + high + " puntos";
  document.getElementById("pol-media").textContent = medium + " a " + (high - 1) + " puntos";
  document.getElementById("pol-baja").textContent = "menos de " + medium + " puntos";
  const total = Math.max(100, high + 20); // la regla muestra 0 a 100 puntos; arriba de eso sigue siendo alto
  const set = (id, from, to) => document.getElementById(id).style.setProperty("--w", ((to - from) / total) * 100 + "%");
  set("regla-baja", 0, medium);
  set("regla-media", medium, high);
  set("regla-alta", high, total);
  document.getElementById("kpi-alta-sub").textContent = "puntaje ≥ " + high;
  document.getElementById("kpi-media-sub").textContent = "puntaje " + medium + "–" + (high - 1);
  document.getElementById("kpi-baja-sub").textContent = "puntaje < " + medium;
}

// --- Carga de datos ---------------------------------------------------------------------------
async function load() {
  api("/api/audit").then((e) => { events = e; renderHistory(); }).catch(() => {});
  if (authRequired) loadSecurity().catch(() => {});
  const coverage = await api("/api/coverage");
  renderCoverage(coverage);
  allAlerts = await api("/api/alerts");
  campaignList = await api("/api/campaigns").catch(() => []);
  applyFilter();
  renderMailboxes();
}

function applyFilter() {
  lastAlerts = filtroEl.value ? allAlerts.filter((a) => a.mailbox_id === filtroEl.value) : allAlerts;
  const active = document.getElementById("filtro-activo");
  const box = lastCoverage.find((c) => c.mailbox_id === filtroEl.value);
  active.hidden = !box;
  active.replaceChildren();
  if (box) {
    active.appendChild(document.createTextNode("Viendo solo los correos de "));
    active.appendChild(el("strong", "", box.label));
    active.appendChild(document.createTextNode(". "));
    active.appendChild(button("Ver todos", "btn btn-ghost", () => { filtroEl.value = ""; applyFilter(); }));
  }
  renderSummary();
  renderCampaigns();
  renderFilters();
  renderList();
  renderDetail();
}

// --- Campanas: el mismo ataque en varios buzones ---------------------------------------------
function renderCampaigns() {
  const box = document.getElementById("campanas");
  box.replaceChildren();
  const live = campaignList.filter((c) => c.actionable > 0);
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

// --- Estado y cifras del panel ----------------------------------------------------------------
// Lo mas importante primero: cuantos correos esperan una decision (rojo solo si hay riesgo alto)
function setEstado(kind, num, title, detail, action) {
  const box = document.getElementById("estado");
  box.className = "panel-estado " + kind;
  document.getElementById("estado-num").textContent = num;
  document.getElementById("estado-titulo").textContent = title;
  document.getElementById("estado-detalle").textContent = detail;
  box.querySelectorAll(".btn").forEach((b) => b.remove());
  if (action) box.appendChild(action);
}

function goDecide() {
  showView("panel");
  ui.filter = "all";
  ui.query = "";
  document.getElementById("buscar-correos").value = "";
  renderFilters();
  renderList();
  const first = listaEl.querySelector(".fila-btn");
  if (first) first.focus();
}

function renderEstado(decide, review) {
  const see = (label, primary) => button(label, primary ? "btn btn-main" : "btn", goDecide);
  if (decide) {
    setEstado("urgente", String(decide),
      decide === 1 ? "correo requiere tu decisión" : "correos requieren tu decisión",
      "Atalaya los marcó como riesgo alto. No aísla ni borra nada sin tu aprobación." + (review ? " Además hay " + review + " para revisar." : ""),
      see(readOnly ? "Ver los correos" : "Decidir ahora", !readOnly));
  } else if (review) {
    setEstado("revisar", String(review),
      review === 1 ? "correo para revisar" : "correos para revisar",
      "Riesgo medio o bajo: míralos cuando puedas. Nada urgente.", see("Revisar", false));
  } else {
    const n = lastCoverage.length;
    setEstado("ok", "✓", "Todo en orden",
      n ? "No hay correos pendientes. Atalaya sigue vigilando " + n + (n === 1 ? " buzón." : " buzones.") : "Conecta un buzón para empezar a vigilarlo.");
  }
}

function showLoadError(err) {
  setEstado("error", "!", "No pudimos cargar el panel",
    (err && err.message ? err.message + " " : "") + "Comprueba tu conexión e inténtalo otra vez.",
    button("Reintentar", "btn btn-main", () => { load().then(() => say("Listo: el panel se cargó.", "ok")).catch(showLoadError); }));
  listaEl.replaceChildren();
}

function renderSummary() {
  const decide = allAlerts.filter((a) => a.priority === 0).length;
  const pend = allAlerts.filter((a) => a.priority <= 1).length;
  renderEstado(decide, pend - decide);
  const badge = document.getElementById("n-correos");
  badge.textContent = String(pend);
  badge.classList.toggle("sin-n", pend === 0);
  badge.classList.toggle("urgente", decide > 0);
  // Cifras reales: conteos de las alertas que Atalaya guarda
  document.getElementById("kpi-total").textContent = String(lastAlerts.length);
  document.getElementById("kpi-total-sub").textContent = lastAlerts.length === 1 ? "correo revisado" : "correos revisados";
  ["high", "medium", "low"].forEach((r, i) => {
    document.getElementById("kpi-" + ["alta", "media", "baja"][i]).textContent = String(lastAlerts.filter((a) => a.risk === r).length);
  });
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
    const li = el("li", "buzon");
    const info = el("div", "info");
    info.appendChild(el("strong", "", i.label));
    info.appendChild(el("span", "muted", " · " + INVITE_TEXT[i.status] + " · vence " + formatDate(i.expires_at)));
    li.appendChild(info);
    if (i.status === "pending") {
      li.appendChild(button("Revocar", "btn btn-ghost", async () => {
        try { await api("/api/invites/" + encodeURIComponent(i.id) + "/revoke", "POST"); await loadInvites(); }
        catch (err) { invMsg.textContent = err.message; }
      }));
    }
    invList.appendChild(li);
  });
  if (!invites.length) invList.appendChild(el("li", "muted", "Aún no hay invitaciones. Escribe un nombre arriba y pulsa «Crear enlace»."));
}

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
    const created = await api("/api/invites", "POST", { label: invLabel.value });
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
    go: () => { setMenu(true, false); const b = document.getElementById("btn-rol"); if (b && !b.hidden) b.focus(); } },
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
document.getElementById("buscar-lista").addEventListener("input", () => { ui.listaLimit = PAGE; renderMailboxes(); });
document.getElementById("solo-atencion").addEventListener("change", () => { ui.listaLimit = PAGE; renderMailboxes(); });
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
  for (let i = 0; i < 4; i++) { const sk = el("li", "fila-correo esqueleto"); sk.setAttribute("aria-hidden", "true"); listaEl.appendChild(sk); }
  detalleEl.querySelector("#detalle-cuerpo").replaceChildren(detailEmpty());
  const health = await (await fetch("/health")).json();
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
    api("/api/me").then((me) => {
      const yo = document.getElementById("yo");
      yo.textContent = "Sesión: " + me.id;
      yo.hidden = false;
    }).catch(() => {});
  }
  api("/api/policy").then((p) => { policy = p; renderPolicy(); }).catch(() => renderPolicy());
  const who = await api("/api/whoami").catch(() => ({ role: "admin", demo_roles: false }));
  readOnly = who.role === "supervisor";
  if (readOnly) {
    document.getElementById("banner-rol").hidden = false;
    ["btn-invitar", "reset"].forEach((id) => { document.getElementById(id).hidden = true; });
  }
  const toggle = document.getElementById("btn-rol");
  if (!who.demo_roles) toggle.hidden = true;
  if (who.demo_roles) {
    toggle.classList.remove("reserva");
    toggle.textContent = readOnly ? "Volver a administración" : "Ver como supervisor";
    toggle.title = toggle.textContent;
    toggle.addEventListener("click", async () => {
      try {
        await api("/api/demo/role", "POST", { role: readOnly ? "admin" : "supervisor" });
        if (!readOnly) tourDone(3);
        window.location.reload();
      } catch (err) {
        say(err.message, "error");
      }
    });
  }
  startTour(mode === "demo" && !readOnly && !!who.demo_roles);
  await load();
}

init().catch((err) => { showLoadError(err); });

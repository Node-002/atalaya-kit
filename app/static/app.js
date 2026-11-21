// Panel de Atalaya (administracion). Todo contenido dinamico se inserta con
// textContent (nunca innerHTML), asi que el texto de un correo no puede ejecutar codigo.
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
const INVITE_TEXT = { pending: "Pendiente", used: "Usada", expired: "Vencida", revoked: "Revocada" };
const GROUPS = [
  { key: "decidir", short: "Por decidir", match: (a) => a.priority === 0, title: "Requieren tu decisión ahora", urgent: true, collapsed: false },
  { key: "revisar", short: "Para revisar", match: (a) => a.priority === 1, title: "Para revisar", collapsed: false },
  { key: "cuarentena", short: "En cuarentena", match: (a) => a.priority === 2, title: "En cuarentena (fuera de la bandeja)", collapsed: true },
  { key: "revisados", short: "Revisados", match: (a) => a.priority === 3, title: "Revisados (con tu decisión y su motivo)", collapsed: true },
  { key: "sinriesgo", short: "Sin riesgo", match: (a) => a.priority === 4, title: "Sin riesgo (Atalaya no vio nada sospechoso)", collapsed: true },
];

// --- Preferencias de la vista (solo del navegador; no son datos de correos) ---
const UI_KEY = "atalaya-vista";
function loadUi() {
  try {
    const saved = JSON.parse(localStorage.getItem(UI_KEY) || "{}");
    return { collapsed: saved.collapsed || {}, filter: "all" };
  } catch {
    return { collapsed: {}, filter: "all" };
  }
}
const ui = loadUi();
function saveUi() {
  try { localStorage.setItem(UI_KEY, JSON.stringify({ collapsed: ui.collapsed })); } catch { /* sin almacenamiento */ }
}
const cardOpen = new Map(); // id de alerta -> abierta o cerrada (se conserva al refrescar)
let lastAlerts = []; // lo que se ve en «Correos» (con el filtro de buzón)
let allAlerts = [];
let campaignList = [];
const PAGE = 24; // buzones por pagina: legible con 50 o 200
const view = { resumenLimit: PAGE, listaLimit: PAGE, groupLimit: {} };
const norm = (t) => t.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const matches = (c, q) => !q || norm(c.label + " " + c.account).includes(norm(q));
let lastCoverage = [];

const alertsEl = document.getElementById("alertas");
const msgEl = document.getElementById("mensaje");
const covEl = document.getElementById("coverage");
const filtroEl = document.getElementById("filtro");
const buzonesEl = document.getElementById("buzones");

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

function button(label, cls, onClick) {
  const b = el("button", cls, label);
  b.type = "button";
  b.addEventListener("click", onClick);
  return b;
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

const REVIEW_OUTCOME = {
  mark_legit: "Revisado: era legítimo",
  reject_quarantine: "Revisado: se dejó sin aislar",
};

function statusText(alert) {
  if (alert.status === "quarantined") return "En cuarentena";
  if (alert.reviewed) {
    const human = alert.actions.filter((a) => REVIEW_OUTCOME[a.type]);
    if (human.length) return REVIEW_OUTCOME[human[human.length - 1].type];
  }
  return STATUS_TEXT[alert.status];
}

function actionLabel(action) {
  if (action.type.startsWith("label:")) return "Etiqueta «" + action.type.slice(6) + "»";
  return ACTION_TEXT[action.type] || action.type;
}

// --- Alertas ------------------------------------------------------------------------------
function renderAlert(alert) {
  const card = el("details", "card " + alert.risk);
  card.open = cardOpen.has(alert.id) ? cardOpen.get(alert.id) : alert.priority === 0;
  card.addEventListener("toggle", () => cardOpen.set(alert.id, card.open));
  const fila = el("summary", "fila");
  fila.appendChild(el("span", "dominio", alert.sender_domain));
  fila.appendChild(el("span", "badge " + alert.risk, RISK_TEXT[alert.risk]));
  fila.appendChild(el("span", "badge estado", statusText(alert)));
  const meta = formatDate(alert.received_at) + (multiple && alert.mailbox_label ? " · " + alert.mailbox_label : "");
  fila.appendChild(el("span", "muted meta", meta));
  card.appendChild(fila);
  const body = el("div", "detalle");
  card.appendChild(body);

  if (alert.explanation_source !== "rules") {
    const resumen = el("p", "resumen-ia");
    resumen.appendChild(
      el("span", "tag", alert.explanation_source === "ai" ? "Resumen con IA" : "Resumen simulado (sin IA real)"),
    );
    resumen.appendChild(document.createTextNode(" " + alert.explanation.replace(/^Resumen simulado:\s*/, "")));
    body.appendChild(resumen);
  }

  if (!alert.signals.length) {
    body.appendChild(el("p", "porque", "Todo parece normal."));
  } else {
    const top = alert.signals.reduce((a, b) => (b.weight > a.weight ? b : a));
    const why = el("p", "porque");
    why.appendChild(el("strong", "", "Motivo: "));
    why.appendChild(document.createTextNode(top.description));
    body.appendChild(why);
    const tech = el("details", "tecnico");
    tech.appendChild(el("summary", "", "Detalle técnico (" + alert.signals.length + (alert.signals.length === 1 ? " señal" : " señales") + ")"));
    const ul = el("ul", "signals");
    alert.signals.forEach((s) => ul.appendChild(el("li", "", s.description + " (" + s.weight + " puntos)")));
    tech.appendChild(ul);
    body.appendChild(tech);
  }

  if (alert.status === "quarantined") {
    body.appendChild(el("p", "nota", "Este correo está fuera de la bandeja, bajo la etiqueta «Sospechoso». «Sacar de cuarentena» lo devuelve a la bandeja y te pide el motivo."));
  }

  const actions = el("div", "actions");
  if (!readOnly && alert.status !== "quarantined") {
    const needs = alert.quarantine_needs_reason;
    actions.appendChild(button("Poner en cuarentena", alert.status === "pending_approval" ? "btn btn-danger" : "btn", () =>
      act(alert.id, "approve", "Correo puesto en cuarentena: salió de la bandeja y quedó guardado en la etiqueta «Sospechoso». No se borró nada.",
        needs ? { title: "Poner en cuarentena", help: "Atalaya no lo marcó como riesgo alto. Explica por qué lo aíslas: queda en el informe del correo." } : null)));
  }
  if (!readOnly && alert.status === "pending_approval") {
    actions.appendChild(button("Dejarlo donde está", "btn", () =>
      act(alert.id, "reject", "Se conservó la etiqueta, sin aislar el correo.",
        { title: "Dejarlo donde está", help: "Atalaya lo marcó como riesgo alto y vas a dejarlo en la bandeja. Explica por qué: queda en el informe del correo." })));
  }
  if (!readOnly && (alert.status === "quarantined" || (alert.risk !== "low" && alert.status !== "dismissed"))) {
    const restoring = alert.status === "quarantined";
    actions.appendChild(button(restoring ? "Sacar de cuarentena" : "Es legítimo", "btn btn-primary", () =>
      act(alert.id, "legit", restoring ? "Sacado de cuarentena: el correo volvió a la bandeja de entrada." : "Marcado como legítimo: el correo volvió a la bandeja de entrada.",
        { title: restoring ? "Sacar de cuarentena" : "Es legítimo",
          help: restoring ? "Vas a devolver el correo a la bandeja. Explica por qué no era peligroso: queda en el informe del correo." : "Explica por qué este correo es legítimo: queda en el informe del correo." })));
  }
  const reportUrl = "/api/alerts/" + encodeURIComponent(alert.id) + "/report";
  const view = el("a", "btn btn-ghost", "Ver informe");
  view.href = reportUrl;
  view.target = "_blank";
  view.rel = "noopener";
  actions.appendChild(view);
  const download = el("a", "btn btn-ghost", "Descargar informe");
  download.href = reportUrl + "?download=true";
  download.setAttribute("download", "");
  actions.appendChild(download);
  body.appendChild(actions);

  if (alert.actions.length) {
    const ul = el("ul", "linea");
    alert.actions.forEach((a) => {
      const li = el("li", "");
      const who = a.by === "atalaya" ? "Atalaya" : actorLabel(a.by);
      li.appendChild(el("span", "muted", formatDate(a.at) + " · "));
      li.appendChild(el("strong", "", who + ": "));
      li.appendChild(document.createTextNode(actionLabel(a)));
      if (a.reason) li.appendChild(el("div", "motivo", "Motivo: " + a.reason));
      ul.appendChild(li);
    });
    body.appendChild(ul);
  }
  return card;
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

async function act(id, verb, okMessage, reasonSpec) {
  try {
    let body;
    if (reasonSpec) {
      const reason = await askReason(reasonSpec);
      if (reason === null) return; // se canceló: no se hace nada
      body = { reason };
    }
    await api("/api/alerts/" + encodeURIComponent(id) + "/" + verb, "POST", body);
    msgEl.textContent = okMessage;
    await load();
  } catch (err) {
    msgEl.textContent = err.message;
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

  buzonesEl.replaceChildren();
  const lq = document.getElementById("buscar-lista").value.trim();
  document.getElementById("lista-buscar").hidden = coverage.length < 8;
  const listed = coverage.filter((c) => matches(c, lq));
  const moreList = document.getElementById("lista-mas");
  moreList.hidden = listed.length <= view.listaLimit;
  moreList.textContent = "Mostrar más (" + Math.max(0, listed.length - view.listaLimit) + " restantes)";
  listed.slice(0, view.listaLimit).forEach((c) => {
    const ok = c.status === "connected";
    const li = el("li", "buzon");
    const info = el("div", "info");
    info.appendChild(el("strong", "", c.label));
    info.appendChild(el("span", "muted", " · " + c.account));
    li.appendChild(info);
    li.appendChild(el("span", "badge " + (ok ? "low" : "high"), ok ? "Vigilado" : "Sin cobertura"));
    if (!readOnly) li.appendChild(button("Desconectar", "btn btn-ghost", () => disconnect(c)));
    buzonesEl.appendChild(li);
  });
  if (!coverage.length) buzonesEl.appendChild(el("li", "muted", "Todavía no hay buzones. Usa «Invitar buzón»."));

  // filtro: conserva la seleccion
  const selected = filtroEl.value;
  filtroEl.replaceChildren(new Option("Todos los buzones", ""));
  coverage.forEach((c) => filtroEl.appendChild(new Option(c.label, c.mailbox_id)));
  filtroEl.value = coverage.some((c) => c.mailbox_id === selected) ? selected : "";
  multiple = coverage.length > 1;
  lastCoverage = coverage;
}

async function disconnect(box) {
  if (!window.confirm("¿Desconectar " + box.label + "? Atalaya dejará de vigilar ese correo y se revocará su acceso.")) return;
  try {
    await api("/api/mailboxes/" + encodeURIComponent(box.mailbox_id), "DELETE");
    msgEl.textContent = "Buzón desconectado.";
    await load();
  } catch (err) {
    msgEl.textContent = err.message;
  }
}

const SECURITY_TEXT = {
  bloqueo: "Dirección bloqueada por demasiados intentos",
  acceso_denegado: "Una cuenta no autorizada intentó entrar",
  ataque_distribuido: "Muchos intentos fallidos desde varias direcciones",
};

async function loadSecurity() {
  const events = await api("/api/security/events");
  const list = document.getElementById("eventos-seguridad");
  list.replaceChildren();
  events.slice(0, 6).forEach((e) => {
    const li = el("li", "");
    li.appendChild(el("strong", "", (SECURITY_TEXT[e.kind] || e.kind) + " "));
    li.appendChild(el("span", "muted", "· " + formatDate(e.at)));
    li.appendChild(el("div", "muted", e.detail));
    list.appendChild(li);
  });
  document.getElementById("seguridad").hidden = !events.length;
}

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

function actorLabel(actor) {
  if (actor === "sistema") return "Atalaya";
  if (actor === "desconocido") return "Persona sin identificar";
  if (actor === "admin-demo") return "Administración (demo)";
  return actor;
}

async function loadHistory() {
  const events = await api("/api/audit");
  const list = document.getElementById("historial");
  list.replaceChildren();
  events.slice(0, 25).forEach((e) => {
    const li = el("li", "evento");
    li.appendChild(el("span", "muted hora-ev", formatDate(e.at)));
    li.appendChild(el("strong", "", " " + (ACTIVITY_TEXT[e.action] || e.action)));
    li.appendChild(el("span", "muted", " · " + actorLabel(e.actor) + (e.detail ? " · " + e.detail : "")));
    list.appendChild(li);
  });
  if (!events.length) list.appendChild(el("li", "muted", "Todavía no hay actividad."));
}

async function load() {
  loadHistory().catch(() => {});
  if (authRequired) loadSecurity().catch(() => {});
  const coverage = await api("/api/coverage");
  renderCoverage(coverage);
  allAlerts = await api("/api/alerts");
  campaignList = await api("/api/campaigns").catch(() => []);
  applyFilter();
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
  render();
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
    info.appendChild(el("span", "muted", " · " + c.sender_domain));
    info.appendChild(el("div", "muted", c.mailboxes.join(", ")));
    card.appendChild(info);
    const n = c.actionable;
    const label = n === c.mailbox_count ? "Poner en cuarentena en los " + n + " buzones" : "Poner en cuarentena los " + n + " restantes";
    if (!readOnly) card.appendChild(button(label, c.pending ? "btn btn-danger" : "btn", () =>
      actCampaign(c, "Cuarentena aplicada a " + n + " correos de la campaña. Nada se borró: puedes sacarlos de cuarentena uno por uno.")));
    box.appendChild(card);
  });
}

async function actCampaign(c, okMessage) {
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
    const res = await api("/api/campaigns/" + encodeURIComponent(c.id) + "/quarantine", "POST", body);
    msgEl.textContent = res.failed ? okMessage + " " + res.failed + " no se pudieron aislar." : okMessage;
    await load();
  } catch (err) {
    msgEl.textContent = err.message;
  }
}

// --- Resumen de la organizacion --------------------------------------------------------------
function timeAgo(iso) {
  if (!iso) return "sin comprobar";
  const secs = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (secs < 60) return "hace unos segundos";
  if (secs < 3600) return "hace " + Math.round(secs / 60) + " min";
  return "hace " + Math.round(secs / 3600) + " h";
}

function focusMailbox(id) {
  filtroEl.value = id;
  applyFilter();
  showTab("correos");
}

function renderSummary() {
  const head = document.getElementById("resumen-org");
  const cards = document.getElementById("resumen-cards");
  const pend = allAlerts.filter((a) => a.priority <= 1).length;
  const uncovered = lastCoverage.filter((c) => c.status !== "connected").length;
  head.replaceChildren(
    pend
      ? el("p", "resumen", pend + (pend === 1 ? " correo espera" : " correos esperan") + " una decisión en " + (lastCoverage.length === 1 ? "tu buzón." : "toda la organización."))
      : el("p", "resumen ok", "Todo en orden: no hay correos pendientes de decisión."),
  );
  if (uncovered) {
    head.appendChild(el("p", "resumen", uncovered + (uncovered === 1 ? " buzón está" : " buzones están") + " sin cobertura: Atalaya no puede vigilarlos hasta que se vuelvan a conectar."));
  }
  const badge = document.getElementById("n-correos");
  badge.textContent = String(pend);
  badge.hidden = pend === 0;

  cards.replaceChildren();
  const q = document.getElementById("buscar-resumen").value.trim();
  const onlyAttention = document.getElementById("solo-atencion").checked;
  document.getElementById("resumen-buscar").hidden = lastCoverage.length < 8;
  const byBox = new Map();
  allAlerts.forEach((a) => { if (!byBox.has(a.mailbox_id)) byBox.set(a.mailbox_id, []); byBox.get(a.mailbox_id).push(a); });
  const need = (c) => (byBox.get(c.mailbox_id) || []).filter((a) => a.priority <= 1).length + (c.status !== "connected" ? 1000 : 0);
  const shown = lastCoverage
    .filter((c) => matches(c, q) && (!onlyAttention || need(c) > 0))
    .sort((a, b) => need(b) - need(a) || a.label.localeCompare(b.label, "es")); // lo urgente primero
  const page = shown.slice(0, view.resumenLimit);
  const more = document.getElementById("resumen-mas");
  more.hidden = shown.length <= page.length;
  more.textContent = "Mostrar más buzones (" + (shown.length - page.length) + " restantes)";
  const note = document.getElementById("resumen-mas-nota");
  note.hidden = lastCoverage.length <= PAGE;
  note.textContent = "Mostrando " + page.length + " de " + lastCoverage.length + " buzones, los que necesitan atención primero.";
  page.forEach((c) => {
    const mine = byBox.get(c.mailbox_id) || [];
    const ok = c.status === "connected";
    const card = el("button", "cbuzon" + (ok ? "" : " sin-cobertura"));
    card.type = "button";
    card.setAttribute("aria-label", "Ver los correos de " + c.label);
    card.addEventListener("click", () => focusMailbox(c.mailbox_id));
    const top = el("div", "cb-top");
    top.appendChild(el("strong", "", c.label));
    top.appendChild(el("span", "badge " + (ok ? "low" : "high"), ok ? "Con cobertura" : "Sin cobertura"));
    card.appendChild(top);
    card.appendChild(el("div", "muted cb-cuenta", c.account));
    const counts = el("div", "cb-cuentas");
    let any = false;
    GROUPS.forEach((g) => {
      const n = mine.filter((a) => g.match(a)).length;
      if (!n) return;
      any = true;
      counts.appendChild(el("span", "cnt" + (g.urgent ? " urgente" : ""), n + " " + g.short.toLowerCase()));
    });
    if (!any) counts.appendChild(el("span", "muted", "Sin correos todavía"));
    card.appendChild(counts);
    card.appendChild(el("div", "muted cb-chequeo", "Último chequeo: " + timeAgo(c.last_check)));
    cards.appendChild(card);
  });
  if (!lastCoverage.length) cards.appendChild(el("p", "muted", "Todavía no hay buzones. Ve a «Buzones» para invitar a alguien."));
  else if (!page.length) cards.appendChild(el("p", "muted", "Ningún buzón coincide con la búsqueda."));
}

function renderChips() {
  const chips = document.getElementById("chips");
  chips.replaceChildren();
  const make = (key, text, urgent) => {
    const b = button(text, "chip" + (urgent ? " urgente" : ""), () => {
      ui.filter = ui.filter === key ? "all" : key;
      render();
      if (ui.filter !== "all") document.getElementById("alertas").scrollIntoView({ block: "start" });
    });
    b.setAttribute("aria-pressed", String(ui.filter === key));
    chips.appendChild(b);
  };
  make("all", "Todos (" + lastAlerts.length + ")", false);
  GROUPS.forEach((g) => {
    const n = lastAlerts.filter((a) => g.match(a)).length;
    if (n) make(g.key, g.short + " " + n, g.urgent);
  });
  document.getElementById("controles").hidden = lastAlerts.length === 0;
}

function render() {
  const alerts = lastAlerts;
  renderChips();
  const pendientes = alerts.filter((a) => a.priority <= 1).length;
  const nodes = [
    pendientes
      ? el("p", "resumen", pendientes + (pendientes === 1 ? " correo requiere" : " correos requieren") + " tu atención.")
      : el("p", "resumen ok", "Nada pendiente: no hay correos que requieran tu atención."),
  ];
  GROUPS.forEach((g) => {
    const items = alerts.filter((a) => g.match(a));
    if (!items.length) return;
    if (ui.filter !== "all" && ui.filter !== g.key) return;
    const isCollapsed = ui.filter === g.key ? false : (g.key in ui.collapsed ? ui.collapsed[g.key] : g.collapsed);
    const section = el("section", "grupo-sec");
    section.id = "grupo-" + g.key;
    const h = el("h3", "grupo" + (g.urgent ? " urgente" : ""));
    const body = el("div", "grupo-cuerpo");
    body.hidden = isCollapsed;
    const toggle = button("", "grupo-btn", () => {
      const nowCollapsed = !body.hidden;
      body.hidden = nowCollapsed;
      ui.collapsed[g.key] = nowCollapsed;
      toggle.setAttribute("aria-expanded", String(!nowCollapsed));
      chev.textContent = nowCollapsed ? "▸" : "▾";
      saveUi();
    });
    const chev = el("span", "chev", isCollapsed ? "▸" : "▾");
    toggle.setAttribute("aria-expanded", String(!isCollapsed));
    toggle.setAttribute("aria-controls", section.id + "-cuerpo");
    body.id = section.id + "-cuerpo";
    toggle.append(chev, document.createTextNode(" " + g.title + " "), el("span", "n", "(" + items.length + ")"));
    h.appendChild(toggle);
    const limit = view.groupLimit[g.key] || 40;
    items.slice(0, limit).forEach((a) => body.appendChild(renderAlert(a)));
    if (items.length > limit) {
      body.appendChild(button("Mostrar más (" + (items.length - limit) + " restantes)", "btn btn-ghost", () => {
        view.groupLimit[g.key] = limit + 40;
        render();
      }));
    }
    section.append(h, body);
    nodes.push(section);
  });
  alertsEl.replaceChildren(...nodes);
  if (!alerts.length) alertsEl.appendChild(el("p", "", "No hay correos por revisar."));
}

document.getElementById("expandir").addEventListener("click", () => {
  lastAlerts.forEach((a) => cardOpen.set(a.id, true));
  GROUPS.forEach((g) => { ui.collapsed[g.key] = false; });
  saveUi();
  render();
});
document.getElementById("contraer").addEventListener("click", () => {
  lastAlerts.forEach((a) => cardOpen.set(a.id, false));
  render();
});

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
  if (!invites.length) invList.appendChild(el("li", "muted", "Aún no hay invitaciones."));
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

// --- Pestanas ------------------------------------------------------------------------------
const TABS = ["resumen", "correos", "buzones", "historial"];
function showTab(name, focusTab) {
  if (!TABS.includes(name)) name = "resumen";
  TABS.forEach((t) => {
    const selected = t === name;
    const tab = document.getElementById("tab-" + t);
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    document.getElementById("panel-" + t).hidden = !selected;
    if (selected && focusTab) tab.focus();
  });
  if (window.location.hash !== "#" + name) history.replaceState(null, "", "#" + name);
}
document.querySelectorAll(".tabs [role=tab]").forEach((tab) => {
  tab.addEventListener("click", () => showTab(tab.dataset.tab));
  tab.addEventListener("keydown", (event) => {
    const i = TABS.indexOf(tab.dataset.tab);
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step) { event.preventDefault(); showTab(TABS[(i + step + TABS.length) % TABS.length], true); }
  });
});
showTab(window.location.hash.slice(1));

// --- Arranque ------------------------------------------------------------------------------
filtroEl.addEventListener("change", applyFilter);
document.getElementById("buscar-resumen").addEventListener("input", () => { view.resumenLimit = PAGE; renderSummary(); });
document.getElementById("solo-atencion").addEventListener("change", () => { view.resumenLimit = PAGE; renderSummary(); });
document.getElementById("resumen-mas").addEventListener("click", () => { view.resumenLimit += PAGE; renderSummary(); });
document.getElementById("buscar-lista").addEventListener("input", () => { view.listaLimit = PAGE; renderCoverage(lastCoverage); });
document.getElementById("lista-mas").addEventListener("click", () => { view.listaLimit += PAGE; renderCoverage(lastCoverage); });

document.getElementById("reset").addEventListener("click", async () => {
  try {
    await api("/api/demo/reset", "POST");
    msgEl.textContent = "Demostración reiniciada.";
    await load();
  } catch (err) {
    msgEl.textContent = err.message;
  }
});

document.getElementById("btn-salir").addEventListener("click", async () => {
  await fetch("/auth/admin/logout", { method: "POST", headers: { "X-Requested-With": "atalaya" } });
  window.location.href = "/login";
});

async function init() {
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
  const who = await api("/api/whoami").catch(() => ({ role: "admin", demo_roles: false }));
  readOnly = who.role === "supervisor";
  if (readOnly) {
    document.getElementById("banner-rol").hidden = false;
    ["btn-invitar", "reset"].forEach((id) => { document.getElementById(id).hidden = true; });
  }
  if (who.demo_roles) {
    const toggle = document.getElementById("btn-rol");
    toggle.hidden = false;
    toggle.textContent = readOnly ? "Volver a administración" : "Ver como supervisor";
    toggle.addEventListener("click", async () => {
      await api("/api/demo/role", "POST", { role: readOnly ? "admin" : "supervisor" });
      window.location.reload();
    });
  }
  await load();
  document.body.classList.add("animar"); // entrada suave solo al abrir, no en cada refresco
  setTimeout(() => document.body.classList.remove("animar"), 1200);
}

init().catch((err) => { msgEl.textContent = err.message; });

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
  { match: (a) => a.priority === 0, title: "Requieren tu decisión ahora", urgent: true },
  { match: (a) => a.priority === 1, title: "Para revisar" },
  { match: (a) => a.priority === 2, title: "En cuarentena (fuera de la bandeja)" },
  { match: (a) => a.priority === 3, title: "Revisados (con tu decisión y su motivo)" },
  { match: (a) => a.priority === 4, title: "Sin riesgo (Atalaya no vio nada sospechoso)" },
];

const alertsEl = document.getElementById("alertas");
const msgEl = document.getElementById("mensaje");
const covEl = document.getElementById("coverage");
const filtroEl = document.getElementById("filtro");
const buzonesEl = document.getElementById("buzones");

let mode = "demo";
let authRequired = false;
let multiple = false;

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
  const card = el("article", "card " + alert.risk);
  card.appendChild(el("h3", "", "Correo de " + alert.sender_domain));
  const meta = "Recibido: " + formatDate(alert.received_at) + (multiple && alert.mailbox_label ? " · Buzón: " + alert.mailbox_label : "");
  card.appendChild(el("p", "hora", meta));

  const badges = el("div", "badges");
  badges.appendChild(el("span", "badge " + alert.risk, RISK_TEXT[alert.risk]));
  badges.appendChild(el("span", "badge estado", statusText(alert)));
  card.appendChild(badges);

  if (alert.explanation_source !== "rules") {
    const resumen = el("p", "resumen-ia");
    resumen.appendChild(
      el("span", "tag", alert.explanation_source === "ai" ? "Resumen con IA" : "Resumen simulado (sin IA real)"),
    );
    resumen.appendChild(document.createTextNode(" " + alert.explanation.replace(/^Resumen simulado:\s*/, "")));
    card.appendChild(resumen);
  }

  card.appendChild(el("p", "porque", alert.risk === "low" ? "Todo parece normal." : "Por qué desconfiamos:"));
  if (alert.signals.length) {
    const ul = el("ul", "signals");
    alert.signals.forEach((s) => ul.appendChild(el("li", "", s.description)));
    card.appendChild(ul);
  }

  if (alert.status === "quarantined") {
    card.appendChild(el("p", "nota", "Este correo está fuera de la bandeja, bajo la etiqueta «Sospechoso». «Sacar de cuarentena» lo devuelve a la bandeja y te pide el motivo."));
  }

  const actions = el("div", "actions");
  if (alert.status !== "quarantined") {
    const needs = alert.quarantine_needs_reason;
    actions.appendChild(button("Poner en cuarentena", alert.status === "pending_approval" ? "btn btn-danger" : "btn", () =>
      act(alert.id, "approve", "Correo puesto en cuarentena: salió de la bandeja y quedó guardado en la etiqueta «Sospechoso». No se borró nada.",
        needs ? { title: "Poner en cuarentena", help: "Atalaya no lo marcó como riesgo alto. Explica por qué lo aislás: queda en el informe del correo." } : null)));
  }
  if (alert.status === "pending_approval") {
    actions.appendChild(button("Dejarlo donde está", "btn", () =>
      act(alert.id, "reject", "Se conservó la etiqueta, sin aislar el correo.",
        { title: "Dejarlo donde está", help: "Atalaya lo marcó como riesgo alto y vas a dejarlo en la bandeja. Explica por qué: queda en el informe del correo." })));
  }
  if (alert.status === "quarantined" || (alert.risk !== "low" && alert.status !== "dismissed")) {
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
  card.appendChild(actions);

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
    card.appendChild(ul);
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
  coverage.forEach((c) => {
    const ok = c.status === "connected";
    const li = el("li", "buzon");
    const info = el("div", "info");
    info.appendChild(el("strong", "", c.label));
    info.appendChild(el("span", "muted", " · " + c.account));
    li.appendChild(info);
    li.appendChild(el("span", "badge " + (ok ? "low" : "high"), ok ? "Vigilado" : "Sin cobertura"));
    li.appendChild(button("Desconectar", "btn btn-ghost", () => disconnect(c)));
    buzonesEl.appendChild(li);
  });
  if (!coverage.length) buzonesEl.appendChild(el("li", "muted", "Todavía no hay buzones. Usa «Invitar buzón»."));

  // filtro: conserva la seleccion
  const selected = filtroEl.value;
  filtroEl.replaceChildren(new Option("Todos los buzones", ""));
  coverage.forEach((c) => filtroEl.appendChild(new Option(c.label, c.mailbox_id)));
  filtroEl.value = coverage.some((c) => c.mailbox_id === selected) ? selected : "";
  multiple = coverage.length > 1;
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
  const query = filtroEl.value ? "?mailbox_id=" + encodeURIComponent(filtroEl.value) : "";
  const alerts = await api("/api/alerts" + query);

  const pendientes = alerts.filter((a) => a.priority <= 1).length;
  const nodes = [
    pendientes
      ? el("p", "resumen", pendientes + (pendientes === 1 ? " correo requiere" : " correos requieren") + " tu atención.")
      : el("p", "resumen ok", "Nada pendiente: no hay correos que requieran tu atención."),
  ];
  GROUPS.forEach((g) => {
    const items = alerts.filter((a) => g.match(a));
    if (!items.length) return;
    const h = el("h3", "grupo" + (g.urgent ? " urgente" : ""), g.title + " ");
    h.appendChild(el("span", "n", "(" + items.length + ")"));
    nodes.push(h, ...items.map(renderAlert));
  });
  alertsEl.replaceChildren(...nodes);
  if (!alerts.length) alertsEl.appendChild(el("p", "", "No hay correos por revisar."));
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

// --- Arranque ------------------------------------------------------------------------------
filtroEl.addEventListener("change", () => load().catch((err) => { msgEl.textContent = err.message; }));

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
  await load();
}

init().catch((err) => { msgEl.textContent = err.message; });

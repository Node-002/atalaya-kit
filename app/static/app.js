// Panel de Atalaya. Todo contenido dinamico se inserta con textContent
// (nunca innerHTML), asi que el texto de un correo no puede ejecutar codigo.
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
  quarantine: "Cuarentena aprobada",
  reject_quarantine: "Cuarentena rechazada",
  mark_legit: "Marcado como legítimo",
};

const alertsEl = document.getElementById("alertas");
const msgEl = document.getElementById("mensaje");
const covEl = document.getElementById("coverage");

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(path, method = "GET") {
  const res = await fetch(path, { method, headers: { "X-Requested-With": "atalaya" } });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail || "Algo salió mal.";
    throw new Error(detail);
  }
  return res.json();
}

function actionLabel(action) {
  if (action.type.startsWith("label:")) return "Etiqueta «" + action.type.slice(6) + "»";
  return ACTION_TEXT[action.type] || action.type;
}

const GROUPS = [
  { priority: 0, title: "Requieren tu decisión ahora", urgent: true },
  { priority: 1, title: "Para revisar" },
  { priority: 2, title: "Ya atendidos" },
  { priority: 3, title: "Sin riesgo" },
];

function formatDate(iso) {
  return new Date(iso).toLocaleString("es-PA", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function renderAlert(alert) {
  const card = el("article", "card " + alert.risk);
  card.appendChild(el("h3", "", "Correo de " + alert.sender_domain));
  card.appendChild(el("p", "hora", "Recibido: " + formatDate(alert.received_at)));

  const badges = el("div", "badges");
  badges.appendChild(el("span", "badge " + alert.risk, RISK_TEXT[alert.risk]));
  badges.appendChild(el("span", "badge estado", STATUS_TEXT[alert.status]));
  card.appendChild(badges);

  card.appendChild(el("p", "porque", alert.risk === "low" ? "Todo parece normal." : "Por qué desconfiamos:"));
  if (alert.signals.length) {
    const ul = el("ul", "signals");
    alert.signals.forEach((s) => ul.appendChild(el("li", "", s.description)));
    card.appendChild(ul);
  }

  const actions = el("div", "actions");
  if (alert.status === "pending_approval") {
    actions.appendChild(button("Poner en cuarentena", "btn btn-danger", () => act(alert.id, "approve", "Correo puesto en cuarentena: salió de la bandeja y quedó guardado en la etiqueta «Sospechoso». No se borró nada.")));
    actions.appendChild(button("Dejarlo donde está", "btn", () => act(alert.id, "reject", "Se conservó la etiqueta, sin aislar el correo.")));
  }
  if (alert.risk !== "low" && alert.status !== "dismissed") {
    actions.appendChild(button("Es legítimo", "btn btn-primary", () => act(alert.id, "legit", "Marcado como legítimo: el correo volvió a tu bandeja de entrada.")));
  }
  card.appendChild(actions);

  if (alert.actions.length) {
    const audit = el("p", "audit");
    audit.textContent = "Historial: " + alert.actions.map(actionLabel).join(" → ");
    card.appendChild(audit);
  }
  return card;
}

function button(label, cls, onClick) {
  const b = el("button", cls, label);
  b.type = "button";
  b.addEventListener("click", onClick);
  return b;
}

async function act(id, verb, okMessage) {
  try {
    await api("/api/alerts/" + encodeURIComponent(id) + "/" + verb, "POST");
    msgEl.textContent = okMessage;
    await load();
  } catch (err) {
    msgEl.textContent = err.message;
  }
}

let mode = "demo";

function renderCoverage(coverage) {
  covEl.replaceChildren();
  coverage.forEach((c) => {
    const ok = c.status === "connected";
    covEl.appendChild(el("span", ok ? "ok" : "bad", ok ? "● Vigilando" : "● Sin cobertura"));
    covEl.appendChild(document.createTextNode(" · " + c.account + " "));
    if (mode === "gmail" && !ok) {
      const link = el("a", "btn btn-primary", "Conectar con Google");
      link.href = "/auth/google/login";
      covEl.appendChild(link);
    }
    if (mode === "gmail" && ok) {
      covEl.appendChild(button("Desconectar", "btn btn-ghost", disconnect));
    }
  });
}

async function disconnect() {
  try {
    await api("/auth/disconnect", "POST");
    msgEl.textContent = "Cuenta desconectada y acceso revocado.";
    await load();
  } catch (err) {
    msgEl.textContent = err.message;
  }
}

async function load() {
  const [alerts, coverage] = await Promise.all([api("/api/alerts"), api("/api/coverage")]);
  renderCoverage(coverage);

  const pendientes = alerts.filter((a) => a.priority <= 1).length;
  const nodes = [];
  nodes.push(
    pendientes
      ? el("p", "resumen", pendientes + (pendientes === 1 ? " correo requiere" : " correos requieren") + " tu atención.")
      : el("p", "resumen ok", "Nada pendiente: no hay correos que requieran tu atención."),
  );
  GROUPS.forEach((g) => {
    const items = alerts.filter((a) => a.priority === g.priority);
    if (!items.length) return;
    const h = el("h3", "grupo" + (g.urgent ? " urgente" : ""), g.title + " ");
    h.appendChild(el("span", "n", "(" + items.length + ")"));
    nodes.push(h, ...items.map(renderAlert));
  });
  alertsEl.replaceChildren(...nodes);
  if (!alerts.length) alertsEl.appendChild(el("p", "", "No hay correos por revisar."));
}

document.getElementById("reset").addEventListener("click", async () => {
  try {
    await api("/api/demo/reset", "POST");
    msgEl.textContent = "Demostración reiniciada.";
    await load();
  } catch (err) {
    msgEl.textContent = err.message;
  }
});

async function init() {
  mode = (await api("/health")).mode;
  const reset = document.getElementById("reset");
  if (mode === "gmail") {
    reset.hidden = true;
    document.getElementById("banner").textContent =
      "Modo conectado: solo para uso local con cuentas de prueba.";
    setInterval(() => load().catch(() => {}), 30000);
    await api("/api/poll", "POST").catch(() => {});
  }
  await load();
}

init().catch((err) => { msgEl.textContent = err.message; });

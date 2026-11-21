// Pagina de consentimiento de quien recibe la invitacion. Solo textContent.
"use strict";

const token = decodeURIComponent(window.location.pathname.split("/").pop() || "");
const consent = document.getElementById("consentimiento");
const invalid = document.getElementById("invalida");
const accept = document.getElementById("acepto");
const connect = document.getElementById("conectar");

async function init() {
  const res = await fetch("/api/public/invite/" + encodeURIComponent(token));
  const info = await res.json();
  if (!info.valid) {
    invalid.hidden = false;
    return;
  }
  document.getElementById("presentacion").textContent =
    "Te invitaron a conectar tu correo (" + info.label + ") para protegerlo contra phishing. " +
    "Quien administra la seguridad de " + info.org + " verá los avisos de seguridad de ese correo." +
    (info.department && info.department !== "Sin área" ? " Tu administración te asignó al área " + info.department + "." : "");
  consent.hidden = false;
  if (info.mode === "demo") document.getElementById("banner-demo").hidden = false;

  accept.addEventListener("change", () => { connect.disabled = !accept.checked; });
  connect.addEventListener("click", () => {
    if (!accept.checked) return;
    const base = info.mode === "demo" ? "/auth/demo/connect" : "/auth/google/login";
    window.location.href = base + "?invite=" + encodeURIComponent(token) + "&consent=1";
  });
}

init().catch(() => { invalid.hidden = false; });

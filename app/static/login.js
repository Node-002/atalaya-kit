"use strict";
const msg = document.getElementById("msg");
const form = document.getElementById("form");

async function init() {
  if (new URLSearchParams(window.location.search).get("error")) {
    document.getElementById("error").hidden = false;
  }
  let options = { google: false, password: false };
  try {
    options = await (await fetch("/api/public/login-options")).json();
  } catch {
    // modo demostracion: no hay acceso de administracion
    window.location.href = "/";
    return;
  }
  document.getElementById("google").hidden = !options.google;
  form.hidden = !options.password;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  msg.textContent = "";
  const res = await fetch("/auth/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Requested-With": "atalaya" },
    body: JSON.stringify({ password: document.getElementById("clave").value }),
  });
  if (res.ok) {
    window.location.href = "/";
    return;
  }
  if (res.status === 429) {
    const minutes = Math.ceil(Number(res.headers.get("Retry-After") || 900) / 60);
    msg.textContent = "Demasiados intentos. Intenta de nuevo en unos " + minutes + " minutos.";
    return;
  }
  msg.textContent = "No se pudo entrar. Revisa la contraseña.";
});

init();

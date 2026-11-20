"use strict";
const msg = document.getElementById("msg");

document.getElementById("form").addEventListener("submit", async (event) => {
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
  const detail = (await res.json().catch(() => ({}))).detail;
  msg.textContent = typeof detail === "string" ? detail : "No se pudo entrar.";
});

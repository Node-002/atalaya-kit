"use strict";
// Intro de inicio: se muestra UNA vez por sesión del navegador y nunca si la persona pidió menos
// movimiento. Solo decide si añade la clase «con-intro»; la animación y su desaparición son CSS.
// Se carga en <head> para que el panel no parpadee antes de la intro.
(() => {
  try {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (sessionStorage.getItem("atalaya_intro")) return;
    sessionStorage.setItem("atalaya_intro", "1");
    document.documentElement.classList.add("con-intro");
  } catch (_) {
    // sin almacenamiento de sesión (modo restringido): no se muestra y el panel carga normal
  }
})();

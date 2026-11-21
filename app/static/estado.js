"use strict";
// Reglas puras del estado de cada correo y de las pestañas de filtro (sin DOM, sin red).
// Se cargan antes de app.js. Cada correo está en UN solo sitio a la vez: las pestañas
// Alta, Media, Baja, Limpios, Cuarentena y Legítimos reparten todos los correos sin repetirlos,
// de modo que sus números suman el total de «Todos».

// Decisiones de una persona (el servidor las guarda en `actions`). La ÚLTIMA manda.
const HUMAN_TYPES = ["quarantine", "reject_quarantine", "mark_legit"];

const lastHuman = (a) => {
  const h = (a.actions || []).filter((x) => HUMAN_TYPES.includes(x.type));
  return h.length ? h[h.length - 1].type : null;
};

// "safe" = correo limpio: riesgo bajo y ninguna señal
const riskKey = (a) => (a.risk === "low" && !(a.signals || []).length ? "safe" : a.risk);

// Dónde está hoy el correo: en cuarentena, resuelto como legítimo, o abierto (sin resolver).
// Primero manda el estado real en la bandeja: si está en cuarentena, ya no es «legítimo» aunque
// antes lo hayan marcado así.
const finalState = (a) => {
  if (a.status === "quarantined") return "quarantine";
  if (lastHuman(a) === "mark_legit") return "legit";
  return "open";
};

const isOpen = (a) => finalState(a) === "open";

const FILTERS = [
  { key: "all", label: "Todos", cls: "todos", match: () => true },
  { key: "high", label: "Alta", cls: "alta", match: (a) => isOpen(a) && a.risk === "high" },
  { key: "medium", label: "Media", cls: "media", match: (a) => isOpen(a) && a.risk === "medium" },
  { key: "low", label: "Baja", cls: "baja", match: (a) => isOpen(a) && riskKey(a) === "low" },
  { key: "safe", label: "Limpios", cls: "limpio", match: (a) => isOpen(a) && riskKey(a) === "safe" },
  { key: "quarantine", label: "Cuarentena", cls: "cuar", match: (a) => finalState(a) === "quarantine" },
  { key: "legit", label: "Legítimos", cls: "legit", match: (a) => finalState(a) === "legit" },
];

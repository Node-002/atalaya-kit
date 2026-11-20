"use strict";
const result = new URLSearchParams(window.location.search).get("result");
document.getElementById(result === "ok" ? "ok" : "cancelado").hidden = false;

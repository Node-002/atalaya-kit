# ADR 0009 — Panel «obsidiana» de tres columnas (fase 1 del rediseño)

- **Fecha:** 2026-11-21
- **Estado:** aceptada.

## Contexto
El usuario diseñó un prototipo visual con Gemini y lo aprobó como nuevo diseño del panel. El prototipo carga Tailwind, Google Fonts y Lucide desde internet, usa `innerHTML` en 15 sitios, muestra cifras inventadas y trae controles que chocan con las reglas del proyecto (umbrales editables, cuarentena automática).

## Decisión
1. **Disposición:** menú lateral con la marca (torre y nombre «Atalaya»), lista de correos al centro y detalle a la derecha. Menú: Panel de control, Buzones, Historial y «Cómo se calcula el riesgo».
2. **Sin recursos externos:** CSS propio con variables (tokens) en `style.css`; fuentes del sistema; iconos como sprite local `app/static/icons/sprite.svg` (Lucide, licencia ISC, nota en `LICENSE-lucide.txt`; solo los usados). La CSP `default-src 'self'` no cambia: ni scripts ni estilos en línea. Los anchos de barras se asignan por JS con `style.setProperty`, que la CSP permite.
3. **Seguridad del DOM:** solo `textContent` y nodos creados a mano; una prueba prohíbe `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval` y `new Function`. Se comprobó con un buzón y un correo hostiles (`<img onerror>`, `<script>`): no se crea ningún elemento.
4. **Los umbrales no se editan.** El prototipo trae deslizadores (80 y 45); se quitaron. Se añade `GET /api/policy` → `{"medium":30,"high":60}`, de solo lectura (cualquier otro método da 405), que lee `app/decision.py`. La sección «Cómo se calcula el riesgo» lo muestra.
5. **Nunca cuarentena automática.** Se quitó «cuarentena automática en puntaje ≥ 95». El motivo escrito (10 a 500 caracteres) sigue exigido en los tres casos de siempre, con el mismo cuadro `askReason` y la misma regla del servidor.
6. **Roles:** igual que antes. El servidor devuelve 403 al supervisor; el panel además oculta los botones. El alternador de rol existe solo en la demo (cookie).
7. **Honestidad de datos:** solo conteos de las alertas reales. No se muestran campos que Atalaya no guarda (asunto, remitente completo, destinatario, URL, IP, país, Return-Path). El puntaje es la suma de pesos de las señales (como `decision.score`), en «pts»; la barra se limita al 100 %.
8. **Responsivo:** ≥ 1100 px, tres columnas; 800–1099 px, el detalle es un panel que se abre sobre la lista, con velo, «Volver a la lista» y Esc; < 800 px, el menú es un cajón y el detalle una pantalla propia.
9. **Historial en CSV** generado en el navegador a partir de `/api/audit` y de las decisiones de las alertas; no se guarda nada nuevo. Las celdas que empiezan con `= + - @` llevan una comilla delante (inyección de fórmulas).
10. **Sin pantalla de inicio** (la del prototipo era opcional): no aporta a la demo y costaría rendimiento. Queda anotado como posible mejora.

## Consecuencias / riesgos
- `login.html`, `invite.html` y `connected.html` comparten `style.css` y heredan la paleta oscura; no se rediseñaron.
- Las pruebas de la versión anterior que dependían de ids concretos se conservaron (`btn-rol`, `n-correos`, `guia`, `mensaje`).
- Huecos para fases siguientes (no hechos): analítica con series de tiempo, antigüedad del dominio (RDAP), IP de origen y país, marca imitada estructurada, comparación por departamento.

# Informe — UI fase 1 (panel «obsidiana», tres columnas)

Rama: `claude/ui-fase1-849e97` (sale de `claude/informes-pdf-843051`; sin push ni merge).
Alcance: `app/static/` (`index.html`, `style.css`, `app.js`, `icons/`), `GET /api/policy` en `app/main.py`, pruebas y docs. `login`, `invite` y `connected` solo heredan la paleta. Decisión de arquitectura: `docs/adr/0009-panel-obsidiana-tres-columnas.md`.

## 1. Qué quedó
- **Tres columnas:** menú con la marca y las secciones (Panel de control, Buzones, Historial, Cómo se calcula el riesgo), lista de correos y detalle del correo.
- **Panel de control:** tarjeta «N correos requieren tu decisión» (como antes), cuatro cifras reales (analizados, alto, medio, bajo; los umbrales salen de `/api/policy`), campañas con su botón, filtros Todos / Alta / Media / Baja / Cuarentena / Legítimos con conteo, búsqueda por dominio o buzón, selector de buzón y una fila por correo con barra de puntaje.
- **Detalle:** insignias de riesgo y estado, puntaje, acciones (las mismas tres, con el mismo cuadro de motivo), «Ver informe», «Descargar PDF» y «Descargar texto»; pestaña **Análisis** («¿Por qué Atalaya detectó esta amenaza?» como lista numerada con las señales reales y el resumen etiquetado «con IA» o «simulado», más qué pasó con el correo) y pestaña **Ficha técnica** (dominio, buzón, hora, identificador, puntaje, autenticación SPF/DKIM/DMARC, señales con su código).
- **Buzones («Usuarios conectados»):** quién está vigilado y quién sin cobertura, sus correos pendientes, último chequeo, «Ver sus correos» y «Desconectar» (solo administración); búsqueda y «Mostrar más» para 200 buzones.
- **Historial:** actividad reciente, ver o descargar el informe de la organización (PDF y texto) y **Exportar a CSV** (en el navegador, a partir de `/api/audit` y las decisiones con su motivo; no se guarda nada).
- **Cómo se calcula el riesgo:** solo lectura. Alto ≥ 60, medio ≥ 30, bajo < 30 (valores de `app/decision.py`), con qué hace Atalaya en cada nivel, lo que nunca hace y cuándo pide motivo.
- **Se conserva:** guía de 3 pasos, aviso de demo, «Reiniciar demostración», invitar buzón, aviso de seguridad, banners y botón de rol (solo demo), motivo obligatorio, 403 del supervisor.

## 2. Lo del prototipo que NO se llevó (gana la regla)
| Prototipo | Qué se hizo |
|---|---|
| Tailwind, Google Fonts y Lucide por internet | CSS propio con tokens, fuentes del sistema, sprite SVG local (Lucide, ISC) |
| 15 `innerHTML` | Ninguno; solo `textContent` y nodos |
| Deslizadores 80 / 45 («Configuración de Auditoría») | Quitados; sección de solo lectura con 60 / 30, valores reales |
| «Cuarentena automática en score ≥ 95» | Quitada; toda cuarentena la aprueba una persona |
| 412 correos/min, 99,4 %, 184 ms, 18 492, +8,4 %, SOC v3.0, TLP:AMBER, Sentinel Engine | No aparecen; solo conteos reales |
| Varias organizaciones, departamentos, Microsoft 365, formulario «Conectar buzón» | No aparecen; se usa «Invitar buzón» (enlace de un solo uso) |
| Asunto, remitente completo, destinatario, URL, IP, país, Return-Path | No se muestran: Atalaya no los guarda |
| Selector de rol en el menú | Solo en la demo (cookie); en modo conectado el rol sale del inicio de sesión |
| Pantalla de inicio de marca (opcional) | No hecha (ver ADR) |
| Textos de 10 px en gris tenue | Mínimo 12 px; texto atenuado `#a3b0c4`, textos de riesgo en tonos claros |
| Analítica, departamentos | Fuera de alcance (fases siguientes) |

## 3. Medidas (Lighthouse, demo en `127.0.0.1:8050`)
| | Antes | Después |
|---|---|---|
| Escritorio: rendimiento / accesibilidad / buenas prácticas / SEO | 100 / 100 / 100 / 100 | **100 / 100 / 100 / 100** |
| Escritorio CLS | 0 | 0,009 |
| Móvil: rendimiento | 100 | **98–99** (6 corridas) |
| Móvil: accesibilidad / buenas prácticas / SEO | 100 / 100 / 100 | 100 / 100 / 100 |
| Móvil CLS | 0 | 0 (0,069 en una corrida antes del arreglo de abajo) |

Dos hallazgos propios que corregí al medir: (1) el botón «Invitar buzón» en móvil quedó sin nombre accesible (accesibilidad 95 → 100 con `aria-label`); (2) un salto de diseño intermitente en móvil (CLS 0,205 en 1 de 3 corridas), porque la tarjeta de estado y la de campañas aparecían con otra altura que su marcador: ahora reservan su sitio con `min-height` por ancho. Lighthouse devolvió a veces `NO_NAVSTART` (fallo conocido de la herramienta, ver el informe de diseño): se repitió hasta tener 6 corridas válidas.

## 4. Verificación
- **`pytest`: 444 pasan** (433 + 11 nuevas en `app/tests/test_ui_fase1.py`: `/api/policy` da 30/60 y 405 con PUT/POST/PATCH/DELETE, el supervisor puede leerla, sin deslizadores ni cuarentena automática, sin recursos externos en HTML/CSS/JS, sin `innerHTML` y similares, iconos locales con licencia, ids de las vistas y banners).
- `ruff check .` limpio; `ruff format --check` limpio en lo nuevo (`app/main.py` ya venía sin formatear de antes y no lo reformateé para no mezclar cambios); `bandit` sin problemas; `pip-audit` sin vulnerabilidades; `gitleaks` sin fugas.
- **axe-core** (wcag2a/aa, 2.1aa y buenas prácticas) en Panel, Panel con detalle, Ficha, Buzones, Historial, Cómo se calcula y Supervisor, a 1366, 800 y 412 px: 0 violaciones (corregí una lista con hijos inválidos y una región con scroll sin foco). Sin desbordamiento horizontal en ningún ancho.
- **Flujo real en el navegador:** «Es legítimo» pide motivo, uno de 5 letras se rechaza, uno válido marca el correo y el filtro «Legítimos» pasa a 1; el CSV incluye la decisión con su motivo; el supervisor no ve botones de acción ni «Invitar» pero sí «Descargar PDF»; Esc cierra el detalle y devuelve el foco a la fila (800 y 412 px). Consola sin errores.
- **200 buzones y 200 alertas simulados** (respuestas inyectadas, con texto hostil `<img onerror>` / `<script>`): carga en 1,2 s, lista de 40 en 40, buzones de 24 en 24, la búsqueda filtra, y no se crea ningún elemento inyectado.

## 5. Capturas (`docs/img/ui-fase1/`)
Nombres `antes-<ancho>-<vista>.png` y `despues-<ancho>-<vista>.png`, con ancho 1366 / 800 / 412.

| Vista | Antes | Después |
|---|---|---|
| Panel | `resumen`, `correos` | `panel` |
| Panel con correo seleccionado | (la tarjeta se abría en la lista) | `panel-detalle`, `panel-ficha` |
| Buzones | `buzones` | `buzones` |
| Historial | `historial` | `historial` |
| Cómo se calcula el riesgo | no existía | `politica` |
| Supervisor | `supervisor` | `supervisor` |
| Menú en móvil | — | `412-menu` |

## 6. Decisiones (todas reversibles)
Acción principal en azul (`#2563eb`, texto blanco con contraste AA) porque el azul claro del prototipo es el color de «riesgo bajo»; rojo solo para riesgo alto. El puntaje se muestra como la suma real de pesos («145 pts»), sin recortarlo a 100 (solo la barra se limita). «Legítimos» = correos que una persona marcó como legítimos. Sin pantalla de inicio. Las páginas de acceso, invitación y conexión quedan oscuras por herencia de la paleta.

## 7. Lo que no pude verificar / pendientes
- No probé el modo conectado (Gmail) con un inicio de sesión real: solo su ruta de código (rol desde `/api/whoami`, que no cambió) y las pruebas existentes.
- No revisé a ojo `login`, `invite` y `connected` con la paleta nueva (comparten las clases; las pruebas pasan).
- Solo Chrome; ni Safari/Firefox ni móvil físico. Los 800 y 412 px son ventanas emuladas.
- Contraste revisado con axe en los estados cargados y con Lighthouse; no medí a mano cada combinación de tonos con transparencia.
- Descarga de CSV: verifiqué el contenido del archivo, no el diálogo de descarga del navegador.
- Huecos anotados para fases siguientes: analítica con series de tiempo, antigüedad del dominio (RDAP), IP de origen y país, marca imitada estructurada, comparación por departamento.

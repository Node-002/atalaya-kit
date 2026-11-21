# Informe de diseño del panel — 21 nov

Rama: `claude/diseno-8f026d` (sale de `endurecimiento`; sin push ni merge).
Alcance: `app/static/` (`index.html`, `style.css`, `app.js`; `login`, `invite` y `connected` heredan los estilos). No se tocó `main.py`, `store.py`, `demo_sessions.py` ni los analizadores.

## 1. Medidas antes y después

Lighthouse sobre `http://127.0.0.1:8010/` (demo), Chrome headless. Móvil = 412 px con throttling `devtools` (ver nota).

| | Antes | Después |
|---|---|---|
| Escritorio: rendimiento / accesibilidad / buenas prácticas / SEO | 99 / 100 / 100 / 100 | **100 / 100 / 100 / 100** |
| Escritorio: CLS | 0,0026 | 0,00005 |
| Móvil: rendimiento | 79 | **94** |
| Móvil: accesibilidad / buenas prácticas / SEO | 100 / 100 / 100 | 100 / 100 / 100 |
| **Móvil: CLS** (umbral bueno 0,1) | **0,187** | **0,0066** |

Un script con `puppeteer-core` (red 4G lenta, CPU ×4, `PerformanceObserver` de `layout-shift`) dio lo mismo: 0,188 antes y 0,007 después.

Nota sobre el método: con el throttling por defecto (simulado) el CLS móvil ya salía ≈0,001, porque ese modo no reproduce el orden real de llegada de los recursos. El 0,187 solo aparece con throttling `devtools` (el que mide de verdad la red lenta), así que ése es el que se usó antes y después.

## 2. Causa real del CLS móvil

El elemento reportado era `main`, pero `main` solo se movía porque **la cabecera cambiaba de alto** al llegar los datos (la medida lo mostró: `main` bajaba de y=243 a y=297 de un solo salto).

1. En móvil `.top-actions` pasaba de una línea a dos: al aparecer «Ver como supervisor» junto a «Invitar buzón», los botones no cabían en una fila. Eso empujó 54 px todo lo de abajo (≈0,186 del total).
2. Los arreglos anteriores no funcionaban por un error de CSS: `[hidden] { display: none !important; }` gana a cualquier regla que intente reservar el hueco. Por eso ni el espacio reservado de `#btn-rol` ni el de `.tab-n[hidden]` servían (la insignia desplazaba las pestañas 23–26 px).

Corrección: ningún elemento reservado usa ya `hidden`; ocupa su sitio con `visibility: hidden` (clases `reserva` y `sin-n`) y JS solo cambia la clase. La cabecera móvil tiene una estructura fija (título, línea de estado, fila de botones de 44 px sin salto de línea), y el resumen carga con un esqueleto y una tarjeta de estado de alto fijo. Un test (`test_header_reserves_its_space_so_the_page_does_not_jump`) vigila que nadie vuelva a poner `hidden` ahí. Dato adicional: un nombre de clase repetido (`.vacio`) rompió la insignia durante el desarrollo; ahora son distintos.

## 3. Qué se mejoró (método de diseñador)

1. **Jerarquía**: nueva tarjeta de estado al inicio del Resumen con un número grande: «3 correos requieren tu decisión» + botón «Decidir ahora» que lleva directo a ese grupo. Si no hay riesgo alto pasa a ámbar («para revisar»), y si todo va bien a verde («Todo en orden»).
2. **Espacio y alineación**: escala de espaciado de 4 px (`--s1…--s7`), contenedor de 880 px, cabecera con icono del escudo.
3. **Color con significado fijo** (documentado al inicio de `style.css`): rojo = solo riesgo alto; ámbar = atención/avisos/errores/«sin cobertura»; verde = bien/legítimo/vigilado; azul = acción principal e información. Cambios: «sin cobertura» y los avisos ya no son rojos; «Poner en cuarentena» pasó de rojo a azul (es una acción, no un riesgo) y «Es legítimo» a verde suave.
4. **Tokens y escala tipográfica**: variables de color, espacio, tamaños (`--fs-xs…--fs-hero`), radios, sombra y movimiento.
5. **Retroalimentación**: el aviso de cada acción es ahora flotante arriba (antes quedaba fuera de pantalla si pulsabas más abajo), con color según resultado, y se apaga solo; el botón pulsado muestra «Procesando…» y se desactiva.
6. **Estados vacíos y de error**: «Bandeja tranquila», «Todavía no hay buzones» (con botón), «Ningún buzón coincide», «Todavía no hay actividad»; si el panel no carga, tarjeta ámbar con «Reintentar».
7. **Guía de primera visita** (solo demo, administración): tarjeta flotante «Paso 1 de 3 — Mira la campaña / Aíslala con tu aprobación / Cambia a supervisor». Cada paso tiene su botón, se marca solo al hacerlo, se cierra con «Ahora no» o Esc y se reabre desde el enlace «Ver guía de 3 pasos» del aviso de demostración. Es `role="region"`, no roba el foco y no mueve el contenido (es `position: fixed`). Solo guarda en `localStorage` qué pasos se hicieron.
8. **Movimiento sutil**: entrada de paneles y tarjetas, elevación al pasar sobre un buzón, brillo en esqueletos, caída suave del aviso. Todo se apaga con `prefers-reduced-motion: reduce`.

Seguridad intacta: CSP `default-src 'self'` sin cambios, cero estilos o scripts en línea (hay un test), solo `textContent`, sin dependencias nuevas.

## 4. Capturas (`docs/img/`)

| Vista | Antes | Después |
|---|---|---|
| Escritorio, Resumen | `antes-escritorio-resumen.png` | `despues-escritorio-resumen.png` |
| Escritorio, Correos | `antes-escritorio-correos.png` | `despues-escritorio-correos.png` |
| Móvil 412, Resumen | `antes-movil-resumen.png` | `despues-movil-resumen.png` |
| Móvil 412, Correos | `antes-movil-correos.png` | `despues-movil-correos.png` |
| Aviso tras aislar la campaña + guía en el paso 3 | — | `despues-escritorio-aviso.png` |

## 5. Verificación

- `pytest`: **329 pasan** (325 previas + 4 nuevas en `app/tests/test_panel_design.py`); `ruff check .` limpio.
- Recorrido real con Chrome headless: la guía avanza al hacer cada paso, aislar la campaña muestra el aviso verde, el número del Resumen baja de 3 a 1, el modo supervisor oculta la guía y las acciones; consola sin errores.

## 6. Lo que no pude verificar / pendientes

- No probé `login`, `invite` y `connected` a ojo: heredan los estilos nuevos (los tests de seguridad pasan) pero no les tomé captura.
- No se probó en un móvil físico ni en Safari/Firefox, solo Chrome.
- En modo supervisor el aviso morado aparece al cargar y mueve el contenido (no es la vista medida por Lighthouse; se puede reservar igual si importa).
- Lighthouse falló al azar con `NO_NAVSTART` con `--headless=new`; funcionó con `--headless=old` y con la ruta de salida absoluta.
- La guía móvil muestra solo el título y los botones (el texto largo se oculta para no tapar el contenido).
- El servidor del puerto 8000 (del usuario) consumía una CPU alta (≈680 s de procesador acumulados); no lo toqué.
- Decisiones tomadas sin preguntar: «Poner en cuarentena» en azul, aviso flotante, guía flotante en vez de una franja fija. Son fáciles de revertir.

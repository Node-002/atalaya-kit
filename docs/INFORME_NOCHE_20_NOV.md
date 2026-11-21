# Informe de la noche del 20 de noviembre: qué se hizo y por qué

> Escrito la noche del viernes 20 nov 2026, mientras dormías. Todo está en la rama local **`integracion`** (15 commits sobre `hackathon/mvp`). **No se subió nada a GitHub** y `hackathon/mvp` no se tocó. Lo que se verificó y lo que no, está marcado con claridad.

## 1. Resumen en 30 segundos
- Tres sesiones trabajaron en paralelo, cada una en su rama: **marcas**, **despliegue** e **interfaz**. Las tres fusionaron sin conflictos.
- Pruebas: de **180 a 314** y todas pasan. `ruff`, `bandit`, `gitleaks` y `pip-audit` limpios sobre la rama integrada.
- Revisé a mano el panel de demostración integrado: las pestañas cargan, no hay errores en la consola y la acción de campaña puso en cuarentena el mismo ataque en los 2 buzones.
- **Lo que NO se pudo verificar:** la imagen Docker (Docker no está instalado en tu equipo), el despliegue real en Render o Railway, las campañas y el supervisor contra Gmail real con Google, y la IA real (sin saldo).

## 2. Por qué estas tres cosas
Los criterios del jurado pesan: problema 30 %, demo real 25 %, negocio 25 %, experiencia 20 %.

| Frente | Criterio que mueve | Razón |
|---|---|---|
| Despliegue demo | Demo real (25 %) | Sin un enlace público que funcione, no hay demo que juzgar. |
| Interfaz de organización y campañas | Negocio (25 %) y experiencia (20 %) | El valor para una empresa o universidad es ver todos los buzones y aislar un ataque que llega a varios de una vez. |
| Marcas | Problema (30 %) y demo (25 %) | Con 3 bancos, probar «Google» o «Microsoft» no detectaba nada. |

## 3. Sesión «marcas» (rama `claude/marcas-fed83c`)
**Qué se hizo**
- 19 palabras de marca nuevas (Google/Gmail, Microsoft/Outlook/Office365, Netflix, Dropbox, PayPal, Apple/iCloud, Amazon, Facebook, DHL, Banistmo, Banco Nacional de Panamá, Davivienda, Yappy, Tigo, Cable & Wireless), cada una con sus dominios oficiales. En total, 22 palabras.
- Detección de errores de escritura en marcas de 6 o más letras (`goggle`, `micros0ft`, `paypa1`).
- Revisión extra por iniciativa propia: ~35 casos adversos. Corregidos: punto final en dominios (`google.com.`), acortadores con puerto o punto final, `paypal.com@evil.example` (ahora analiza el host real), guiones partiendo la marca (`pay-pal`), marca más palabra de estafa (`googleacc`, `securepaypal`) y un falso positivo de «responder a» desde un subdominio del mismo dominio.
- 18 correos sintéticos nuevos en el corpus (48 en total) y `app/tests/test_brands.py`.

**Por qué:** la pista principal de muchos ejemplos reales (como los de la Universidad de York) es un dominio que imita a la marca, y Atalaya solo lo veía con 3 bancos.

**Cómo se verificó:** `python -m app.evaluate` antes y después. No se cambió ningún peso ni umbral.

| Medida | Corpus de 48, código anterior | Corpus de 48, código nuevo |
|---|---|---|
| Phishing detectado | 11/24 (46 %) | 21/24 (88 %) |
| Falsos positivos | 3/24 | 3/24 (los mismos de siempre) |

**Lectura honesta (la escribió la propia sesión y la comparto):** esa mejora es poco informativa, porque los casos nuevos se escribieron para la función nueva. En los 30 correos originales no cambió nada. No es una estimación del rendimiento real.

**Límites que quedan**
- Los dominios oficiales están escritos de memoria y hay que verificarlos. Si falta uno legítimo, por ejemplo `googleusercontent.com`, esos correos se marcarían como falsos.
- Un dominio legítimo con la palabra de una marca corta (`apple-huerto`) o a una letra de una larga (`amazona`) se marcará. Mitigación: la acción siempre pide aprobación humana.
- No se detecta `rnicrosoft` (`rn` por `m`).
- **Decisiones que dejé abiertas a propósito:** enlaces a una IP, y correos sin cabecera `Authentication-Results`. Resolverlos exigiría un peso nuevo y no lo toqué.

## 4. Sesión «despliegue» (rama `claude/despliegue-cf5173`)
**Qué se hizo**
- `Dockerfile` y `.dockerignore`: Python 3.12, usuario sin privilegios, puerto desde `PORT`, `--proxy-headers`, y `ATALAYA_MODE=demo` **escrito en el propio comando**, de modo que una variable mal puesta en la plataforma no puede activar el modo con Gmail.
- La imagen solo copia `requirements.txt` y `app/`: fuera quedan `.env`, `.git`, `.venv`, `data/` y las pruebas.
- Cabecera `Strict-Transport-Security` cuando la URL base es https; además `Permissions-Policy` (cámara, micrófono y geolocalización apagados) y `Cross-Origin-Opener-Policy: same-origin`.
- Pruebas que demuestran que en demo no existen `/auth/google/*`, `/auth/admin/*`, `/api/me` ni `/api/security/events`.
- `docs/DESPLIEGUE.md`: paso a paso para Render y Railway, comprobaciones y lista previa a «Submit and publish». ADR 0004.
- `pip-audit`: sin vulnerabilidades conocidas.

**Por qué:** el enlace público lo abrirá gente desconocida. El modo con Gmail guarda tokens reales y no debe existir en internet.

**No verificado:** Docker no está instalado aquí, así que la imagen **nunca se construyó**. El primer despliegue en Render puede revelar un error de arranque. Por eso en el cronograma el despliegue va el sábado, con margen, y no el domingo.

## 5. Sesión «interfaz» (rama `claude/interfaz-8b5dec`)
**Qué se hizo**
1. **Pestañas** Resumen, Correos, Buzones e Historial. Se conservó todo lo anterior (grupos, contadores, motivo obligatorio, informe, invitaciones).
2. **Resumen por buzón:** estado de cobertura, contadores y último chequeo, y al tocar una tarjeta se filtra por ese buzón. Lo urgente va primero.
3. **Campañas** (con tu permiso): el mismo ataque en 2 o más buzones se muestra como «1 campaña en N buzones», con una acción para aislarlo en todos. Misma regla de motivo, una entrada de auditoría por alerta, reversible, no borra ni envía. Solo se guardan hashes, no remitente ni asunto. Si falta el motivo en alguna alerta, **no se toca ninguna** (422).
4. **Supervisor de solo lectura** (con tu permiso): `ATALAYA_SUPERVISOR_EMAILS`, mismo inicio de sesión con Google. Ve el panel, el historial, los informes y el reporte de la organización. El **servidor** devuelve 403 en cualquier escritura (no solo se ocultan botones). En la demo hay un botón para alternar entre administrador y supervisor.
5. **Pulido:** movimiento sutil que respeta `prefers-reduced-motion`, avisos más claros, contraste, foco de teclado, móvil, páginas de login y consentimiento.
6. **Revisión de seguridad y escala (por iniciativa propia):** pruebas de que todo endpoint exige sesión, CSRF antes que otras comprobaciones, topes de tamaño y ningún `innerHTML`. Para 50 a 200 buzones: caché de 60 s del estado de conexión, búsqueda, paginación y «Mostrar más». Con 200 buzones, sondear y agrupar tarda menos de 5 s (prueba).
7. Documentación: ADR del panel, `docs/MVP_ALCANCE.md` (anota que campañas y supervisor entraron con tu permiso) y `docs/USO_DE_IA.md`.

**Por qué:** una organización con varios buzones necesita ver quién está cubierto y que el mismo ataque llegó a varias personas, y quien supervisa necesita ver sin poder actuar. Es el argumento de negocio del proyecto.

**Límites**
- Una campaña con remitente y asunto distintos en cada buzón no se agrupa (se prefirió no agrupar a agrupar mal).
- Un solo rol de lectura; no hay permisos por buzón ni jerarquías.
- Las campañas y el supervisor no se probaron con **dos buzones reales de Google** (tienes solo una cuenta de prueba conectada).

## 6. Lo que hice yo al integrar
- Fusioné las tres ramas en `integracion` y corrí todo: **314 pruebas**, `ruff`, `bandit`, `gitleaks` (38 commits, sin hallazgos) y `pip-audit`.
- Detecté que dos sesiones habían creado un ADR con el mismo número 0004. Renombré el del panel a **0005** y actualicé la referencia en `docs/MVP_ALCANCE.md`.
- `bandit` falló una vez por un error de codificación al imprimir letras cirílicas de las pruebas. Con `PYTHONUTF8=1` corre bien: 0 problemas de severidad media o alta.
- Levanté la demo desde la rama integrada: Resumen con 3 buzones, pestaña Correos con «1 campaña en 2 buzones», acción de campaña ejecutada y estados comprobados por la API (los 2 correos pasaron a cuarentena). Consola sin errores. Cerré ese servidor temporal.

## 7. Decisiones que te tocan
1. **Revisar y aceptar la rama `integracion`** (te propongo hacerlo mirando la demo 10 minutos). Si te gusta, la fusiono en `hackathon/mvp` y la subo tras pasar `gitleaks`.
2. **Verificar los dominios oficiales** de las marcas (lista en `app/analyzers.py`). Puedo proponerte los que faltan, pero no deben quedar de memoria.
3. **Enlaces a una IP y correos sin `Authentication-Results`:** ¿agrego una señal nueva con peso nuevo? Cambia la calibración, por eso no lo hice.
4. **Comprar saldo de la API** (opcional) para probar la IA real. Sigue sin verificarse el nombre del modelo ni el costo por correo.

## 8. Lo que sigue sin existir (para decirlo con honestidad en el pitch)
- Sin aprendizaje a partir de las decisiones humanas.
- Una sola organización, con administradores configurados en `.env`.
- Microsoft 365 y el acceso a nivel de dominio de Workspace no están construidos.
- El corpus es sintético y pequeño. No hay evidencia de clientes reales.
- Google en modo de pruebas: máximo 100 usuarios y tokens que caducan a los 7 días.

# Análisis del proyecto por áreas (sábado 21 nov 2026, mañana)

## Cómo se calculó (y qué NO es)
Se sigue el mismo principio de las listas de endurecimiento del Departamento de Defensa de EE. UU. (las guías **DISA STIG**, que se evalúan con herramientas tipo SCAP/OpenSCAP) y de los **CIS Benchmarks**: una lista de controles concretos, cada uno se comprueba y el porcentaje es *controles cumplidos ÷ controles evaluados*. Para aplicaciones web el equivalente más usado es **OWASP ASVS**, y de ahí salen casi todos los controles de seguridad.

- **Cumple = 1 punto, parcial = 0,5, no cumple = 0.**
- **No es una certificación oficial.** Es una lista que armé yo y evalué sobre este código; sirve para decidir en qué invertir las horas que quedan, no para presumir de un número.
- Los puntos de cada área son del mismo peso entre sí. Un fallo pequeño y uno grave cuentan igual; por eso al final están los hallazgos **ordenados por gravedad**.
- Todo lo marcado «verificado» se comprobó hoy con comandos. Lo que no se pudo probar está marcado así.


> **Actualización del 21 nov (tras el endurecimiento):** global **~65 %**. Seguridad 90 % (demo sin `/docs`, con límites de uso y sin cabecera `Server`), código 77 % (dependencias fijadas y CI creado, aún sin ejecutarse), experiencia 75 % (una copia de la demo por visitante y Lighthouse 100 de accesibilidad), entrega 54 % (README veraz). Despliegue, privacidad y detección no cambiaron. Detalle y evidencias en `docs/INFORME_ENDURECIMIENTO_21_NOV.md`. Las tablas de abajo son las del análisis inicial.

## Resultado global: **60 %**
```
Seguridad            ████████████████░░░░  80 %   (16 / 20)
Código y calidad     █████████████░░░░░░░  64 %   (7 / 11)
Experiencia de uso   █████████████░░░░░░░  63 %   (7,5 / 12)
Optimización         ████████████░░░░░░░░  61 %   (5,5 / 9)
Despliegue y operac. ████████████░░░░░░░░  59 %   (6,5 / 11)
Privacidad y legal   ███████████░░░░░░░░░  55 %   (5,5 / 10)
Detección (producto) ██████████░░░░░░░░░░  50 %   (6 / 12)
Entrega y negocio    █████████░░░░░░░░░░░  46 %   (5,5 / 12)
                     ────────────────────
Promedio             ████████████░░░░░░░░  60 %
```
**Lectura:** lo más sólido es la seguridad. Lo más débil **no es técnico**: es lo que el jurado ve primero (README, enlace público, evidencia, presentación). Esa parte se arregla en horas.

---

## 1. Seguridad: 80 %
| # | Control | Estado | Evidencia |
|---|---|:--:|---|
| 1 | Secretos fuera del repositorio | ✅ | `.env`, `secrets/`, `data/`, `*.db` ignorados; `gitleaks` sin hallazgos en 43 commits |
| 2 | Dependencias sin vulnerabilidades conocidas | ✅ | `pip-audit`: ninguna |
| 3 | Análisis estático | ✅ | `bandit`: 0 problemas en el código de la app |
| 4 | Inicio de sesión del administrador | ✅ | Google OIDC con `state`, `nonce` y lista permitida; probado con cuenta real |
| 5 | Límite de intentos y aviso | ✅ | 5 fallos → bloqueo creciente hasta 24 h; aviso en el panel |
| 6 | Sesiones y cookies | ✅ | del lado del servidor; `HttpOnly`, `SameSite`, `Secure` bajo https |
| 7 | CSRF | ✅ | un POST sin la cabecera recibe 403 (verificado hoy) |
| 8 | Cabeceras de seguridad | ✅ | CSP `default-src 'self'`, `nosniff`, `no-referrer`, `Permissions-Policy`, COOP; `no-store` en la API (verificado hoy) |
| 9 | Escape de contenido (XSS) | ✅ | sin `innerHTML`, `eval` ni `document.write` en `app/static` (verificado hoy) |
| 10 | Permisos por rol | ✅ | el supervisor recibe 403 en cualquier escritura (prueba) |
| 11 | Tokens cifrados en reposo | ✅ | Fernet |
| 12 | Gestión de la clave de cifrado | 🟡 | la clave vive en `.env`; no hay rotación ni gestor de secretos |
| 13 | No guardar cuerpos ni adjuntos | ✅ | solo veredicto, señales y hash |
| 14 | Defensa contra instrucciones ocultas a la IA | 🟡 | diseño correcto (delimitar, JSON validado, la IA no baja el riesgo) y probado con explicador simulado; **nunca con IA real** |
| 15 | Logs sin secretos | ✅ | redacción de tokens y códigos |
| 16 | Auditoría de acciones | ✅ | cada decisión queda con quién y cuándo |
| 17 | Superficie pública mínima | ❌ | `/docs` y `/openapi.json` responden 200 en la demo (lista las 21 rutas); la cabecera `Server: uvicorn` se ve |
| 18 | Límite de uso en la demo pública | ❌ | sin límite en `/api/demo/reset`, `/api/poll`, `/api/invites` |
| 19 | Pruebas de seguridad automáticas | ✅ | `test_security`, `test_panel_security`, `test_supervisor`, etc. |
| 20 | Revisión independiente / prueba de intrusión | ❌ | no hecha (esperable en un hackatón; decirlo) |

**Falta para llegar a ~95 %:** cerrar `/docs` y `/openapi.json` en la demo, ocultar la cabecera `Server`, poner límite de uso en la demo (≈30 min). Los puntos 12, 14 y 20 no se resuelven este fin de semana: se declaran como límites.

## 2. Código y calidad: 64 %
| # | Control | Estado | Evidencia |
|---|---|:--:|---|
| 1 | Linter limpio | ✅ | `ruff`: sin avisos |
| 2 | Pruebas pasan | ✅ | 314 de 314 |
| 3 | Cobertura | ✅ | **94 %** (3 559 líneas; 213 sin probar) |
| 4 | Funciones de tamaño razonable | 🟡 | 3 funciones de más de 60 líneas: `create_app` (405), `build_router` (248), `callback` (84) |
| 5 | Sin código pendiente o muerto | ✅ | cero `TODO` / `FIXME` |
| 6 | Validación de datos en los bordes | ✅ | pydantic v2 |
| 7 | Dependencias fijadas | ❌ | `requirements.txt` sin versiones: una versión nueva podría romper la compilación en Render |
| 8 | Configuración del proyecto | ❌ | no hay `pyproject.toml` ni configuración de `ruff` |
| 9 | Pruebas automáticas al subir código (CI) | ❌ | no hay `.github/workflows` |
| 10 | Decisiones documentadas | ✅ | 5 ADR con fecha |
| 11 | Cobertura de la parte con Google real | 🟡 | `providers/gmail.py` **53 %** y `auth.py` **71 %**: justo lo más difícil de probar sin cuenta real |

**Falta para llegar a ~85 %:** fijar versiones (`pip freeze`), añadir un flujo de GitHub Actions con `pytest`, `ruff` y `gitleaks` (≈30 min). Dividir `create_app` es deseable pero **no** compensa el riesgo ahora.

## 3. Experiencia de uso: 63 %
| # | Control | Estado | Evidencia |
|---|---|:--:|---|
| 1 | Flujo claro (resumen → correos → decisión) | ✅ | pestañas, tarjetas por buzón, grupos |
| 2 | Lenguaje sencillo en español | ✅ | |
| 3 | Acciones con confirmación y motivo | ✅ | motivo obligatorio cuando se va en contra de Atalaya |
| 4 | Accesibilidad | 🟡 | `lang="es"`, 25 atributos `aria-`, foco visible y `prefers-reduced-motion`; **no auditada con herramienta** (axe/Lighthouse) |
| 5 | Móvil | 🟡 | `viewport` y reglas responsive; no lo comprobé en un celular real hoy |
| 6 | Mensajes de error y estados vacíos | 🟡 | existen, sin revisión sistemática |
| 7 | Rapidez percibida | ✅ | API en 2–3 ms; `app.js` 33 KB |
| 8 | Guía para quien abre la demo por primera vez | 🟡 | hay aviso de «datos simulados», pero no un recorrido que diga «prueba esto» |
| 9 | Diseño visual pulido | 🟡 | tu propia valoración: «hay que mejorar el diseño» |
| 10 | Flujo del empleado (invitación → consentimiento → confirmación) | ✅ | probado con Google real |
| 11 | Prueba con personas reales | ❌ | ninguna |
| 12 | Demo pública con estado compartido | ❌ | todos los visitantes comparten los mismos datos: uno que aísle un correo, o pulse «Reiniciar», cambia lo que ve el siguiente (incluido el jurado) |

**Falta para llegar a ~80 %:** el pulido visual de hoy, un mini-recorrido de demo («1. mira la campaña, 2. aíslala, 3. cambia a supervisor») y **dar a cada visitante su propia copia de la demo** (punto 12, el más importante para el jurado).

## 4. Optimización: 61 %
| # | Control | Estado | Evidencia |
|---|---|:--:|---|
| 1 | Latencia de la API | ✅ | mediana **2,2 ms** (50 pruebas, por `127.0.0.1`) |
| 2 | Escala a muchos buzones | ✅ | prueba con 200 buzones: < 5 s |
| 3 | Caché de estado de conexión | ✅ | 60 s |
| 4 | Archivos estáticos livianos | 🟡 | 33 KB + 15 KB + 8 KB, sin compresión ni minificado (insignificante a este tamaño) |
| 5 | Caché del navegador | ✅ | `ETag` en los estáticos |
| 6 | Uso de cuotas de la API de Gmail | 🟡 | máximo 25 correos por vuelta; cuotas reales sin medir |
| 7 | Costo de la IA medido | ❌ | no hay saldo; sin tokens ni costo por correo |
| 8 | Arranque en frío del plan gratuito | 🟡 | documentado (~1 min), sin mitigar |
| 9 | Prueba con muchos visitantes a la vez | ❌ | no hecha |

**Nota importante:** una primera medición salió en **2 segundos** por petición. No era la app: en Windows `localhost` intenta primero IPv6 y espera 2 s. Por `127.0.0.1` son 2 ms. En Render no ocurre, pero si ves lentitud en tu equipo, usa `127.0.0.1:8000`.

## 5. Despliegue y operación: 59 %
| # | Control | Estado | Evidencia |
|---|---|:--:|---|
| 1 | Dockerfile seguro | ✅ | revisado: usuario sin privilegios, solo `app/`, modo demo forzado |
| 2 | Imagen construida y probada | ❌ | Docker no instalado; nunca se construyó |
| 3 | Demo pública en línea | ❌ | no desplegada |
| 4 | HTTPS / HSTS / proxy | 🟡 | configurado y probado en pruebas; sin verificar en vivo |
| 5 | Comprobación de salud | ✅ | `/health` |
| 6 | Modo demo imposible de cambiar desde afuera | ✅ | escrito en el `CMD` |
| 7 | Persistencia del modo real | ✅ | SQLite cifrado |
| 8 | Respaldo y recuperación | ❌ | `data/` solo local |
| 9 | Monitoreo y avisos | 🟡 | aviso en el panel; webhook y correo opcionales sin configurar |
| 10 | Guía de despliegue | ✅ | `docs/DESPLIEGUE.md` |
| 11 | Reinicios | 🟡 | las sesiones viven en memoria: cada reinicio exige volver a entrar |

## 6. Privacidad y cumplimiento: 55 %
| # | Control | Estado | Evidencia |
|---|---|:--:|---|
| 1 | Minimización de datos | ✅ | no se guarda contenido |
| 2 | Consentimiento explícito | ✅ | página de invitación |
| 3 | Borrado al desconectar | ✅ | se eliminan las alertas guardadas |
| 4 | Política de privacidad pública | ❌ | no existe la página |
| 5 | Aviso de que un tercero (Anthropic) recibe texto enmascarado | 🟡 | documentado en el diseño; revisar si el consentimiento lo dice |
| 6 | Verificación de Google para el permiso `gmail.modify` | ❌ | hoy solo «modo de pruebas» (máx. 100 usuarios, tokens de 7 días); producción exige verificación y una auditoría de seguridad externa |
| 7 | Licencia del repositorio | ❌ | no hay `LICENSE` |
| 8 | Documento de ética y legal | ✅ | `docs/ETICA_LEGAL_SEGURIDAD.md` |
| 9 | Términos de uso | ❌ | no existen |
| 10 | Enmascarado de datos personales antes de la IA | ✅ | teléfonos, cuentas y cédulas |

## 7. Detección (calidad del producto): 50 %
| # | Control | Estado | Evidencia |
|---|---|:--:|---|
| 1 | SPF / DKIM / DMARC | ✅ | |
| 2 | Dominios parecidos, letras de otros alfabetos | ✅ | ~35 casos adversos probados |
| 3 | Lista de marcas | 🟡 | 22 palabras; los dominios oficiales están **escritos de memoria** |
| 4 | Enlaces acortados y «responder a» distinto | ✅ | |
| 5 | Instrucciones ocultas a una IA | ✅ | |
| 6 | Medición con el corpus | 🟡 | 21/24 detectados, 3/24 falsos positivos; corpus **sintético** y escrito por nosotros |
| 7 | Fraude sin señales técnicas (jefe pide transferencia, cambio de cuenta) | ❌ | limitación conocida |
| 8 | Adjuntos | ❌ | **no construido** (el README lo promete) |
| 9 | Reputación de enlaces / dominios nuevos | ❌ | **no construido** (el README lo promete) |
| 10 | IA real probada | ❌ | sin saldo |
| 11 | Aprendizaje a partir de las decisiones humanas | ❌ | |
| 12 | Campañas entre buzones | ✅ | construido anoche |

## 8. Entrega y negocio: 46 %
| # | Control | Estado | Evidencia |
|---|---|:--:|---|
| 1 | Problema con fuentes | ✅ | `docs/EVIDENCIA_PUBLICA.md` |
| 2 | Evidencia propia (entrevistas, encuesta) | ❌ | encuesta lista, **sin publicar**; 0 respuestas |
| 3 | Modelo de negocio | 🟡 | documentado, sin validar con nadie |
| 4 | Competencia | ✅ | `docs/COMPETENCIA.md` |
| 5 | README veraz y actual | ❌ | **ver hallazgo 1** |
| 6 | Guion del pitch actual | 🟡 | `PITCH.md` (14 líneas) sigue el guion viejo: no menciona panel, campañas ni supervisor |
| 7 | Presentación (diapositivas) | ❌ | |
| 8 | Video de la demo | ❌ | |
| 9 | Enlace público de la demo | ❌ | |
| 10 | Uso de IA documentado | ✅ | `docs/USO_DE_IA.md` |
| 11 | Límites honestos escritos | ✅ | informe de anoche y resultados de pruebas |
| 12 | Repositorio listo para volverse público | 🟡 | `gitleaks` limpio; falta licencia y revisar el historial |

---

## Hallazgos ordenados por gravedad

### 🔴 Crítico (afecta lo que el jurado lee o ve)
1. **El README promete cosas que no existen.** Dice que Atalaya consulta **Safe Browsing y VirusTotal**, analiza **adjuntos**, usa **RDAP/whois** y **Tailwind**, y que hace *polling* a una «cola». Revisé el código: **nada de eso está** (búsqueda de `virustotal`, `safe browsing`, `rdap`, `tailwind`, `tldextract` sin resultados). Un jurado que compare README y demo lo verá, y bajaría la nota de «problema/negocio» por falta de honestidad. **Arreglo: reescribir el README (30 min).**
2. **No hay enlace público de la demo.** Es el 25 % de la nota («demo real»).
3. **La demo pública comparte estado entre visitantes.** Si dos jueces entran a la vez, o uno pulsa «Reiniciar demostración», se pisan. **Arreglo: una copia de la demo por visitante (cookie), 1 a 2 h.**

### 🟠 Alto
4. **Demo pública sin límite de uso** y con `/docs` y `/openapi.json` abiertos (≈30 min).
5. **Dependencias sin versión fijada**: una actualización de Render podría romper la compilación justo antes de entregar (10 min).
6. **Sin evidencia propia de clientes**: publicar la encuesta hoy (20 min) y enviar 1–2 mensajes de entrevista.
7. **Dominios oficiales de las marcas sin verificar**: riesgo de falsos positivos en una demo en vivo.

### 🟡 Medio
8. Sin `LICENSE`, política de privacidad ni términos (30 min en total).
9. Sin CI ni versiones fijas; cobertura baja justo en las partes con Google real (53 % y 71 %).
10. `PITCH.md` desactualizado; sin diapositivas ni video.
11. Diseño visual: el pulido que me pediste para hoy.

### ⚪ Bajo / aceptado y declarado
12. Gestión de claves, sin pentest independiente, verificación de Google pendiente, sin aprendizaje, sin adjuntos ni reputación de enlaces, funciones largas (`create_app`). Se declaran como límites en el pitch.

## Qué haría yo, en este orden
| Orden | Tarea | Tiempo | Sube |
|---|---|---|---|
| 1 | Reescribir el README con lo que **sí** existe | 30 min | Entrega +, honestidad |
| 2 | Fijar dependencias, cerrar `/docs`, ocultar `Server`, límite de uso en demo | 40 min | Seguridad, Código, Despliegue |
| 3 | Una copia de la demo por visitante | 1–2 h | Experiencia, Demo |
| 4 | Desplegar en Render y probar en ventana privada | 1–2 h | Despliegue, Demo |
| 5 | Publicar la encuesta; enviar 1–2 mensajes | 30 min | Entrega, Problema |
| 6 | Mejora de diseño + mini-recorrido de demo | 2 h | Experiencia |
| 7 | `LICENSE`, política de privacidad y términos (una página corta) | 30 min | Privacidad |
| 8 | CI con GitHub Actions (pytest, ruff, gitleaks) | 30 min | Código |
| 9 | Verificar dominios de marcas y reevaluar el corpus | 45 min | Detección |
| 10 | Pitch (guion nuevo), diapositivas, video | domingo | Entrega |

**Si se hace 1 a 8, el global sube de ~60 % a ~75–78 %**; el porcentaje de «Entrega y negocio» es el que más gana.

## Precauciones
- **No hacer público el repositorio** hasta pasar `gitleaks` sobre todo el historial y tener `LICENSE`.
- **No conectar cuentas reales al despliegue público**; modo demo únicamente.
- **No citar una cifra** de `docs/EVIDENCIA_PUBLICA.md` sin abrir la fuente.
- **Los tokens de Google de prueba caducan a los 7 días**: reconecta antes de grabar el video.
- Sincroniza el reloj de Windows (el recordatorio de las 9:00) antes de volver a iniciar sesión con Google.
- **No presentes la IA como probada**: el resumen que se ve hoy es el simulado.
- Antes de «Submit and publish», probar todos los enlaces en ventana privada.

## Cómo repetir estas mediciones
```
python -m pytest -q --cov=app          # pruebas y cobertura (necesita pytest-cov)
python -m ruff check .
PYTHONUTF8=1 python -m bandit -q -r app -x app/tests
python -m pip_audit -r requirements.txt
gitleaks detect --source .
```

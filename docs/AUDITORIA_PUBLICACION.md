# Auditoría previa a la publicación del repositorio

**Fecha:** 21 nov 2026 · **Alcance:** árbol de trabajo y las 64 confirmaciones de todas las ramas locales (`git log --all`) · **Método:** solo lectura; no se tocó el historial, no se borró nada, no se hizo push.

## Recomendación final (actualizada tras las decisiones del usuario)

**Árbol de trabajo: listo para publicar, salvo las dos decisiones pendientes** (3: estrategia interna; 4: licencia). Los documentos de entrevistas siguen en el repositorio pero saneados (sin teléfonos, correos ni nombres de instituciones, con «0 entrevistas realizadas» dicho con claridad); se quitó «[nombre]» y toda mención de la universidad o situación académica; se cambió el número real de `test_llm.py`. Gitleaks, `pytest` (433 pruebas), `ruff` y `bandit` pasan y las métricas de `python -m app.evaluate` no cambian.

**Historial: sigue conteniendo los datos antiguos** (ver «Qué datos siguen en el historial»). Para hacerlo público hay dos opciones en el MISMO repositorio, comparadas en «Plan de publicación»: **(A)** publicar con el historial tal cual (riesgo bajo-medio) o **(B)** reescribirlo con `git filter-repo` conservando las fechas. **Recomendación:** B si importa no mostrar a qué instituciones se contactó; A si se acepta que se vea. Ambas conservan las fechas de commit; B cambia todos los SHA.

### Estado de las decisiones
| # | Decisión | Estado |
|---|---|---|
| 1 | Documentos de entrevistas | **Tomada:** se quedan, saneados (hecho) |
| 2 | Identidad (nombre de pila, universidad, situación académica) | **Tomada:** quitar del árbol (hecho). Se conservan el usuario de GitHub y el nombre de equipo anterior (ya cambiado a «Atalaya») |
| 3 | Estrategia interna (`IDEAS.md`, `pitch/archivo/`, `COMPETENCIA_AUDIO.txt`, `PREGUNTAS_ORGANIZADORES.md`, `CHECKLIST_6AM.md`, borradores de precio) | **Pendiente** |
| 4 | Licencia | **Pendiente** |
| 5 | ¿Repositorio nuevo o el mismo? | **Tomada:** el mismo, para conservar el historial y sus fechas como evidencia |

## Resumen de lo comprobado

| Control | Resultado |
|---|---|
| `gitleaks detect --log-opts="--all"` | **0 hallazgos** (64 commits, ~920 KB) |
| Patrones a mano (`sk-ant`, `AIza`, `GOCSPX`, `ghp_`, `BEGIN … PRIVATE KEY`, `client_secret`, `refresh_token`, `FERNET_KEY=`, `API_KEY=`) en árbol e historial | Solo nombres de variables en código y valores falsos en pruebas (`"fake-not-real"`). Sin valores reales |
| `.env`, `secrets/`, `data/`, `*.db`, `token*.json`, `*.pem`, `*.key`, `*.log`, `*.wav` alguna vez añadidos (`git log --all --diff-filter=A`) | **Nunca**. Solo `.env.example` (sin valores), `.claude/launch.json` y `app/tokens.py` |
| Identificadores de cuenta Google (`ouid=`), IP reales, rutas `C:\Users\…` | Ninguno. Solo IP de documentación (`1.2.3.4`, `192.168.1.1`, `8.8.8.8` en pruebas) |
| Autoría (`%an/%ae/%cn/%ce`) | 67 commits `Node-002 <346905662+Node-002@users.noreply.github.com>`; 4 de `dependabot[bot]` (noreply). Sin correo personal |
| Mensajes de commit | Sin datos sensibles. Llevan `Co-Authored-By: Claude … <noreply@anthropic.com>` (público y esperado) |
| Archivos borrados en el historial | Ninguno (`--diff-filter=D` vacío): nada «escondido» en commits antiguos |
| Tamaño | Mayor objeto 178 KB (`pitch/archivo/FacturaCR_pitch.pptx`). Sin binarios pesados |
| Imágenes (`docs/img/*.png`, `logo/*`) | Vistas 5 representativas + metadatos de las 14 en la rama actual (sin EXIF/texto incrustado). Solo la demo con datos simulados (`@empresa-demo.example`, «Carlos Perez - Ventas»), informes PDF de la demo y el logo. Sin correos reales, avatares, cuentas, IP ni pestañas del navegador. Las 40 capturas `docs/img/ui-fase1/` están en la rama `ui-fase1`, no en esta (misma demo; revisar al integrarlas) |

## Hallazgos (por gravedad)

| # | Gravedad | Qué | Dónde | Por qué importa | Qué hacer |
|---|---|---|---|---|---|
| 1 | **Alta** (árbol: resuelto; historial: abierto) | Teléfonos y WhatsApp de instituciones contactadas: una consultora de TI ([teléfono omitido], [teléfono omitido]), una universidad privada ([teléfono omitido], WhatsApp [teléfono omitido]), el área de TI de una universidad pública ([teléfono omitido], [teléfono omitido], [teléfono omitido]) | `docs/ENTREVISTAS_OBJETIVOS.md` líneas 81, 105, 112, 125; `docs/CORREOS_ENTREVISTAS.md` línea 10. Presentes en 68 commits de cada archivo (desde `dd302f2`/`cc34852` hasta hoy) y en todas las ramas | Son canales institucionales públicos, pero el repositorio revelaría **a qué organizaciones se escribió** y expondría sus números a quien lo lea; el propio documento prohíbe publicarlo | Decisión 1. Quitar del árbol **y** del historial (repositorio nuevo) |
| 2 | **Alta** | Teléfono institucional real usado como dato falso en una prueba: `[teléfono omitido]` (el WhatsApp de una universidad privada) | `app/tests/test_llm.py` líneas 37 y 55; en 59 commits | Vincula el repositorio con la lista de contactos y pone un número real en código. Está en `app/`, que esta tarea no toca | Cambiar por un número inventado, p. ej. `[teléfono omitido]`, en la sesión que posee `app/tests/`; luego squash (decisión 1) |
| 3 | **Alta** | Lista de instituciones/correos contactados y estado de las gestiones: `[correo omitido]`, `[correo omitido]`, `[correo omitido]`, `[correo omitido]`, `[correo omitido]`, `[correo omitido]`, CSIRT, una empresa de TI, una empresa de TI, una empresa de TI, C&W | `docs/CORREOS_ENTREVISTAS.md`, `docs/ENTREVISTAS_OBJETIVOS.md`, `docs/PLAN_ENTREVISTAS_SABADO.md` |situación académica| Decisión 1 |
| 4 | Media | Identidad del usuario: nombre de pila «[nombre]» y «estudiante de [universidad]» y su situación académica; usuario de GitHub `Node-002`; nombre de equipo anterior (ya cambiado a «Atalaya») | `docs/ENTREVISTAS_GUIA.md:27`, `docs/CORREOS_ENTREVISTAS.md:3,18,32`, `docs/ENTREVISTAS_OBJETIVOS.md`, `docs/ESTADO_INICIAL.md`, `app/tests/fixtures/corpus.json:30` («[nombre] <contacto@gmail.com>»), `docs/GUIA_ACTIVAR_HERRAMIENTAS.md` | Un nombre de pila no es grave; la universidad y el estado de matrícula sí identifican a una persona y pueden afectar su situación académica | Decisión 2. Quitar con los documentos de entrevistas; en `corpus.json` cambiar «[nombre]» por «Persona» (otra sesión) |
| 5 | Media | Documentos de estrategia interna: ideas descartadas (FacturaCR, `docs/IDEAS.md`), presentación `pitch/archivo/FacturaCR_pitch.pptx` (idea antigua, 8 láminas; metadatos genéricos «PptxGenJS», sin autor), borradores de precio («hipótesis»), competencia, preguntas a los organizadores, lista de pasos de entrega | `docs/IDEAS.md`, `pitch/archivo/`, `docs/COMPETENCIA*.md`, `docs/PREGUNTAS_ORGANIZADORES.md`, `docs/CHECKLIST_6AM.md`, `docs/CHECKLIST_ENTREGA.md`, `docs/NEGOCIO_*.md`, `docs/CRONOGRAMA*.md`, `PRD.md` | No hay secretos ni personas. Es estrategia: el jurado la verá. Es decisión de comodidad, no de seguridad. `COMPETENCIA_AUDIO.txt` es un guion de voz para el usuario (tuteo: «Tenés razón en dudar»), no apto como documento público | Decisión 3 |
| 6 | Media | **Falta `LICENSE`** y avisos de terceros | Raíz del repositorio. `docs/LICENCIA_OPCIONES.md` confirma que no se eligió ninguna | Sin licencia, «todos los derechos reservados»: público pero nadie puede legalmente usarlo. El jurado puede preguntarlo | Decisión 4; añadir `LICENSE` y `NOTICE` (ver abajo) |
| 7 | Baja | Cadena de suministro: acciones de GitHub con etiquetas móviles (`@v4`, `@v5`, `@v2`) en lugar de SHA | `.github/workflows/ci.yml` líneas 18, 22, 44 | Una etiqueta puede reapuntarse. Dependabot ya sube versiones en la rama de CI | Anotado: la rama `ci-docker` es de otra sesión. Fijar por SHA al integrarla |
| 8 | Baja | `requirements.txt` fijado (`==`) pero sin hashes; `pypdf` en dev aparece como 6.9.2 en esta rama y 6.21.4 en la rama de Dependabot (confirmación `59f24e5`) | `requirements*.txt` | Sin hashes no se detecta un paquete alterado en PyPI | Opcional: `pip-compile --generate-hashes`. Integrar el bump de pypdf |
| 9 | Baja | `.claude/launch.json` versionado con la ruta local `C:\Hackaton\.venv\…` | `.claude/launch.json` | Revela la carpeta del proyecto, no el usuario (la ruta no contiene `C:\Users\…`) | Opcional: `git rm --cached` y dejarlo local, o publicarlo tal cual. Ya se añadió `.claude/worktrees/`, `.claude/settings.local.json` y `.claude/memory/` al `.gitignore` |
| 10 | Info | El remoto privado `origin` ya tiene ramas de Dependabot (`checkout-7`, `setup-python-7`, `gitleaks-action-3`, `pypdf-6.21.4`) | `origin` | Si se hiciera público el repositorio actual, aparecerían todas las ramas | Otra razón para el repositorio nuevo |

### Sin hallazgos
- Sin tokens de invitación reales ni cookies de sesión en el historial.
- Los correos con `@gmail.com`, `@outlook.com`, `@icloud.com` y `@paypal.com` son ficticios de pruebas (`a@gmail.com`, `maria@gmail.com`, `admin.pdf@gmail.com`, `director.general@gmail.com`).
- Los textos con `onrender.com` (`atalaya-demo.onrender.com`) son la URL de la demo, que debe ser pública.
- No hay scripts de instalación descargados de internet en el repositorio. El `Dockerfile` usa `python:3.12-slim` y `pip install -r requirements.txt` (conviene fijar el digest de la imagen; opcional).

## Licencias de dependencias (fijadas en `requirements.txt`)

Leídas de los metadatos de los paquetes instalados.

- **MIT / BSD / ISC / Apache-2.0 / PSF / MIT-CMU (HPND):** `fastapi`, `starlette`, `pydantic`, `uvicorn`, `httpx`, `anthropic`, `cryptography`, `google-*`, `requests`, `reportlab` (BSD), `pillow` (MIT-CMU), `PyYAML`, etc.
- **Copyleft fuerte (GPL/AGPL/LGPL): ninguno.**
- **`certifi`: MPL-2.0** (copyleft débil por archivo). Se usa sin modificarla, sin incompatibilidad.
- Compatible con publicar bajo MIT, Apache-2.0 o AGPL-3.0.
- **Avisos recomendados en un `NOTICE`:** iconos Lucide (ISC), si la sesión de la interfaz los incluye; fuentes OFL, si las añade; ReportLab (BSD) y Pillow (MIT-CMU), al distribuir el contenedor.
- **Logo y banner (`logo/`):** no hay registro de su origen en el repositorio. Si se generaron con IA o con una fuente tipográfica con licencia, anotarlo en `docs/USO_DE_IA.md` o `NOTICE` antes de publicar.

## Cambios hechos en el árbol (rama `claude/publico-listo-4dd8a4`)

| Archivo | Qué se hizo |
|---|---|
| `docs/CORREOS_ENTREVISTAS.md` | Reescrito como plantilla + registro: tabla de destinatarios con descriptores genéricos y «[contacto omitido]»; estado «0 entrevistas, sin respuesta»; quitadas las frases sobre matrícula y regreso a clases |
| `docs/ENTREVISTAS_OBJETIVOS.md` | Sección de contactos y universidades reescrita con descriptores («una consultora de TI», «una autoridad pública de pymes», «una universidad privada», «el área de TI de una universidad pública», «una asociación de colegios»); quitados teléfonos, correos, URL de instituciones y referencias a ser estudiante de una universidad concreta; aviso de «0 entrevistas» al inicio |
| `docs/ENTREVISTAS_GUIA.md` | «soy [nombre], participante de un hackatón de ciberseguridad» → «soy [tu nombre], participante de un hackatón de ciberseguridad»; igual en la plantilla de correo |
| `docs/PLAN_ENTREVISTAS_SABADO.md` | Aviso de estado real; quitados nombres de instituciones y «estudiante»; «gente de tu universidad» → «de tu entorno» |
| `docs/CRONOGRAMA_POR_CRITERIOS.md`, `docs/MVP_ALCANCE.md` | Nombres de instituciones → descriptores; el dato de Microsoft 365 queda como «una universidad pública» |
| `docs/COMPETENCIA.md` | «Proyecto de un estudiante» → «de una sola persona» |
| `app/tests/fixtures/corpus.json` | «[nombre] <contacto@…>» → «Persona <contacto@…>». `python -m app.evaluate` idéntico antes y después (27/30 = 90 % detectados; 3/32 falsos positivos) |
| `app/tests/test_llm.py` | `[teléfono omitido]` → `[teléfono omitido]` (4 sitios), misma lógica |
| `.gitignore` | `.claude/worktrees/`, `.claude/settings.local.json`, `.claude/memory/` |

Búsqueda de comprobación: se repitió `git grep` con la lista de términos sensibles (guardada fuera del repositorio, porque contiene justo lo que se quiere ocultar); sin resultados salvo falsos positivos.

## Qué datos siguen en el historial (en commits antiguos)

Con la opción A quedan visibles, en todos los commits anteriores a este saneamiento:

| Dato | Dónde (versiones antiguas) | Gravedad |
|---|---|---|
| Nombre de una consultora de TI, una universidad privada y el área de TI de una universidad pública, con sus correos y teléfonos/WhatsApp (publicados por ellas mismas), más una autoridad pública de pymes, CSIRT y proveedores de TI citados | `docs/CORREOS_ENTREVISTAS.md`, `docs/ENTREVISTAS_OBJETIVOS.md`, `docs/PLAN_ENTREVISTAS_SABADO.md` (68 versiones cada uno) y todas las ramas | **Baja-media.** Datos publicados por las propias instituciones, pero la lista revela a quién se contactó y que no respondieron |
| Teléfono institucional usado como dato falso | `app/tests/test_llm.py` (59 versiones) | Baja |
|situación académica| `docs/ENTREVISTAS_GUIA.md`, `docs/CORREOS_ENTREVISTAS.md`, `app/tests/fixtures/corpus.json` | **Baja** el nombre de pila; **media** la situación académica, porque identifica a la persona |
| Estrategia interna (decisión 3 pendiente) | ver hallazgo 5 | Informativa |

No hay secretos, cuentas, IP, rutas con usuario ni correos personales en ningún commit.

## Plan de publicación en el MISMO repositorio

Antes de cualquiera: terminar e integrar el trabajo de las demás ramas en `hackathon/mvp`, resolver las decisiones 3 y 4, añadir `LICENSE` y `NOTICE`, y volver a pasar `gitleaks`, `pytest`, `ruff` y `bandit`. **Ningún comando de abajo se ha ejecutado.**

### Opción A: sanear solo el árbol y dejar el historial como está
- **Qué cambia:** nada en el historial; los SHA y las fechas no se tocan.
- **Qué queda visible:** lo de la tabla anterior, para quien navegue commits antiguos o clone el repositorio.
- **Riesgos:** la lista de instituciones contactadas y la situación académica quedan accesibles. Una vez público, otras personas pueden clonar y conservar el historial: no hay marcha atrás.
- **Ventajas:** cero riesgo técnico; conserva SHA, fechas y referencias de PR.

```powershell
git checkout hackathon/mvp
git merge --no-ff claude/publico-listo-4dd8a4
gitleaks detect --source . --log-opts="--all"
gh repo edit Node-002/atalaya --visibility public --accept-visibility-change-consequences
```

### Opción B: reescribir el historial con `git filter-repo` conservando las fechas
- **Qué cambia:** el contenido de los archivos afectados en todas las versiones y, por tanto, **los SHA** desde el primer commit afectado (en la práctica, todos). Los enlaces a commits antiguos dejan de funcionar.
- **Qué no cambia:** las fechas de autor y de commit, los mensajes, los autores y el orden. `git filter-repo` conserva las fechas por defecto; se verifica abajo.
- **Cómo se refleja en GitHub:**
  - Las referencias `refs/pull/*` y los commits de las solicitudes de extracción (PR) de Dependabot **siguen existiendo en GitHub** y se pueden abrir por su SHA aunque se sobrescriban las ramas. Hay que **cerrar los PR, borrar las ramas remotas** (`dependabot/*`) y **pedir a Soporte de GitHub la purga** de los commits en caché y de las referencias de PR.
  - Forks y clones existentes conservan el historial antiguo: comprobar que no hay (el repositorio es privado).
  - Las ramas de Dependabot se recrean solas en el siguiente escaneo.
  - Las ejecuciones de Actions, comentarios y vistas en caché apuntan a SHA que ya no existirán.
- **Riesgos:** perder el vínculo SHA→evidencia; una expresión mal escrita deja el dato; un clon incompleto pierde ramas. Por eso se trabaja sobre un clon espejo y se conserva intacto el original.
- **Condiciones previas:** detener todas las sesiones y worktrees que escriben en el repositorio (`git worktree list`) y anotar el SHA de cada rama.

**Procedimiento, script y verificaciones:** ver `docs/LIMPIEZA_HISTORIAL.md` y `tools/historial/`. La lista de reemplazos se guarda fuera del repositorio (contiene los datos a retirar). Se ensayó sobre un espejo temporal: 83 commits, mismas fechas, autores, orden y asuntos; cero coincidencias en todas las revisiones; `gitleaks`, `pytest` y `ruff` pasan sobre el resultado.

**Nota:** este informe cita los datos que se retiran (tabla de hallazgos). La limpieza también los sustituye aquí, pero conviene **no publicar este documento** (o publicarlo ya saneado).

Después: reclonar en `C:\Hackaton`. Los clones y worktrees antiguos apuntan a SHA antiguos y **no deben empujarse**: un `git push` de una rama vieja reintroduce los datos.

### Qué evidencia de fechas se conserva en cualquier caso
- **Fechas de autor y de commit:** se conservan en A y en B. Las fija quien comitea y se pueden modificar: sirven, pero no prueban nada por sí solas.
- **Evidencia de GitHub que no depende del contenido:** fecha de creación del repositorio, fecha de creación de PR e incidencias de Dependabot, historial de ejecuciones de Actions (los registros detallados se conservan 90 días por defecto) y los eventos de la cuenta y del repositorio (Events API, unos 90 días). Con B, los SHA que muestran dejarán de coincidir con las ramas.
- **Render:** el historial de despliegues (fecha y hora de cada compilación y SHA desplegado) es evidencia de un tercero. Conviene exportar la lista o capturas antes de reescribir.
- **Respaldo propio antes de B:** guardar en un lugar privado `C:\Hackaton-original.git` y `C:\Hackaton-original-fechas.txt` con su huella (`Get-FileHash`); para dar fuerza probatoria, un recibo de tercero (por ejemplo, enviarse por correo la lista de hashes y fechas).

## Lista de comprobación antes de pulsar «público»

- [ ] Decisiones 3 y 4 tomadas y aplicadas (estrategia interna; `LICENSE` y `NOTICE`).
- [ ] Elegido A o B; si B, ejecutado y verificado como arriba, y purga confirmada por Soporte.
- [ ] `gitleaks detect --source . --log-opts="--all"` sin hallazgos en el repositorio final.
- [ ] `.env`, `data/`, `*.db` ausentes (`git ls-files`).
- [ ] Capturas de `docs/img/ui-fase1/` revisadas al integrarlas (solo demo simulada).
- [ ] Demo y enlaces abiertos en una ventana sin sesión.

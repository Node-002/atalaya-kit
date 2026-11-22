# Descripción del proyecto (texto para el formulario de Dojo y el README)

> Redactada el 22 nov 2026 para reflejar el modelo actual: **kit autoalojado**. Cada organización lo instala y lo opera en sus propios servidores y responde por su instalación; el equipo Atalaya no aloja ni recibe datos y no ofrece soporte. Todo lo que afirma existe hoy en el repositorio; lo no probado se dice como tal.

## Por qué se amplió
Antes la descripción solo decía «agente que vigila el correo». Con el modelo nuevo falta contar cuatro cosas que los jueces van a buscar: **quién lo instala y quién se responsabiliza**, **cómo se vende (como hipótesis)**, **qué no hace** y **cómo se usó la IA para construirlo** (Dojo pide esa evidencia y el formulario no tiene un campo aparte). Se mantiene corta arriba y larga abajo.

## Resumen corto (≈ 300 caracteres)
Atalaya revisa cada correo nuevo de una organización pequeña, explica en español por qué desconfía de un mensaje y deja que una persona decida qué aislar. Se instala en los propios servidores de cada organización: su correo no pasa por nosotros. Código abierto (AGPL-3.0).

## Descripción completa

**El problema.** Colegios, clínicas, pymes y universidades de 5 a 100 buzones no tienen un equipo de seguridad: dependen de que cada persona dude a tiempo de un correo falso. Las soluciones fuertes vienen de grandes proveedores, pensadas para equipos de TI y en inglés, y muchas dicen «bloqueado» sin explicar por qué.

**Qué hace hoy.** Atalaya analiza cada correo nuevo con reglas calculadas por código (SPF/DKIM/DMARC, dominios parecidos a 28 marcas, letras de otros alfabetos, enlaces acortados, «responder a» distinto, urgencia e instrucciones ocultas a una IA), explica el riesgo en español sencillo y pide aprobación humana para lo crítico. La cuarentena es reversible: nada se borra ni se envía. Si alguien decide ir en contra de Atalaya debe escribir el motivo. Un mismo ataque que llega a varios buzones se agrupa como campaña y se aísla con una sola acción. Hay roles de administración y de supervisor de solo lectura, analítica por área e informes en PDF.

**Privacidad por diseño.** No guarda asunto, cuerpo ni adjuntos: solo el veredicto, las señales, un identificador, el estado y metadatos técnicos de las cabeceras, cifrados. La IA solo redacta la explicación, es opcional y viene apagada; el correo se trata como dato hostil y la salida de la IA se valida.

**Por qué un kit autoalojado.** Cada organización instala su propia copia, con su propia aplicación de Google marcada como interna y sus propias claves. El equipo Atalaya no aloja el servicio ni recibe correos, tokens, claves o datos; la organización opera su servidor, guarda sus datos y responde por su instalación. El software se entrega «tal cual» bajo AGPL-3.0, sin soporte ni garantías. Así se evita, además, la verificación de Google que exigiría un servicio que custodie correos de terceros.

**Modelo de negocio (hipótesis, sin clientes todavía).** Licencia del kit por organización, con precio sin definir, y licencia comercial para quien lo use en un producto cerrado (borrador sin revisión legal). Hoja de ruta: hoy Gmail y Google Workspace; después Microsoft 365 con el mismo modelo; más adelante un servicio alojado, cuando Google verifique la aplicación.

**Qué no hace (límites honestos).** No analiza adjuntos ni la reputación de los enlaces (no consulta Safe Browsing, VirusTotal ni similares, por privacidad); solo Gmail y Google Workspace; la IA real está implementada pero no se probó con saldo (en la demo la explicación es simulada); el kit no se verificó con una organización de Google Workspace real (sí arrancó con Docker real). La medición usa 62 correos sintéticos escritos por el desarrollador: 27 de 30 intentos detectados y 3 de 32 legítimos marcados de más; no es rendimiento real.

**Cómo se construyó con IA (agentic coding).** Una persona, con Claude Code como agente de programación, bajo reglas escritas en `CLAUDE.md`: cambios pequeños, pruebas antes de dar algo por terminado, seguridad no negociable y alcance congelado. Cada decisión de arquitectura tiene su ADR (14) y `docs/USO_DE_IA.md` registra qué se pidió, qué generó la IA y qué corrigió o decidió la persona. 569 pruebas automáticas; CI en GitHub Actions (pruebas, imagen Docker con escaneo y kit con instalador).

**Tecnologías.** Python 3.12, FastAPI, Pydantic, SQLite, Gmail API, Claude API (opcional), ReportLab, Docker y GitHub Actions.

**Enlaces.** Demo (datos simulados): https://atalaya-demo.onrender.com · Video: https://youtu.be/QnZj7nNyKBo · Repositorio: https://github.com/Node-002/atalaya-kit

## English version

**Short.** Atalaya reviews every new email in a small organization, explains in plain Spanish why it distrusts a message, and lets a person decide what to quarantine. It is installed on each organization's own servers: their email never passes through us. Open source (AGPL-3.0).

**Long.** Small organizations (5 to 100 mailboxes) have no security team and depend on each person doubting in time. Atalaya analyses each new email with code-calculated rules (SPF/DKIM/DMARC, lookalike and homograph domains of 28 brands, shortened links, reply-to mismatch, urgency, hidden instructions aimed at an AI), explains the risk, and asks for human approval before anything critical. Quarantine is reversible; nothing is deleted or sent. It stores no subject, body or attachments. The AI only writes the explanation; it is optional and off by default.

It is a **self-hosted kit**: each organization installs and runs its own copy, with its own Google app and keys, and is responsible for its installation and data. The Atalaya team does not host the service, does not receive any data, and offers no support or warranty; the software is provided "as is" under AGPL-3.0. Business model is a hypothesis with no customers yet.

**Limits.** No attachment analysis or link reputation (privacy); Gmail/Google Workspace only; the real AI explanation was not tested with credits (the demo is simulated); the kit was not verified with a real Workspace organization. Measured on 62 synthetic emails written by the developer: 27 of 30 attempts detected, 3 of 32 legitimate emails wrongly flagged.

**Built with agentic coding:** one person with Claude Code under written rules (`CLAUDE.md`), 14 architecture decision records, a log of AI use (`docs/USO_DE_IA.md`), 569 automated tests and CI.

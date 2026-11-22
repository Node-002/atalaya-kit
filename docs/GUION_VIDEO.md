# Guion del video de la demo (≈ 2:30)

> Video **opcional** (tiene su propio campo en la entrega). Es una **grabación de pantalla con tu voz**, sin cámara.
> Distinto del pitch: el pitch lo presentas tú en vivo; el video enseña el producto funcionando para quien lo vea sin ti.
> Los nombres de botones salen de la demo del 21 nov: **confírmalos en el ensayo**. Las frases entre «» son una propuesta:
> dilas con tus palabras, pero no afirmes nada que esté marcado como pendiente.

## Antes de grabar (10 min)
- [ ] **Despierta la demo** abriendo `https://atalaya-demo.onrender.com` 2–3 minutos antes (plan gratuito: la primera carga tarda ~1 min).
- [ ] **Ventana privada** y pantalla a **1920×1080**, zoom 100 %. La intro (radar y torre) solo sale **una vez por sesión**: para grabarla, abre una ventana privada nueva en cada toma.
- [ ] Cierra pestañas, marcadores y notificaciones (modo «No molestar»). **No muestres** tu Gmail real, el archivo `.env`, claves, la consola de Google Cloud ni el soporte de GitHub.
- [ ] Verifica que el **último despliegue** está activo: `…/static/intro.js` responde y un error 422 devuelve «Datos no validos.».
- [ ] Micrófono probado; habla pausado. Si te equivocas, repite la frase: se corta en edición.
- [ ] Graba en **tomas cortas por bloque** (abajo) y únelas; es más fácil que una toma de 2:30 sin fallos.

## Tomas

### 0 · Intro (0:00–0:08) — sin voz o con una frase
**Pantalla:** abrir la demo en ventana privada. Se ve la intro: radar, torre y «ATALAYA».
**Voz:** «Atalaya: el agente que vigila el correo de tu organización.»

### 1 · Qué es (0:08–0:25)
**Pantalla:** **Panel de Control**: las cuatro tarjetas (correos analizados y amenazas altas, medias y bajas), «Vigilancia activa · 14 buzones», y el aviso **«Demostración con datos simulados»** (que se vea).
**Voz:** «Una pyme, un colegio o una clínica no tiene equipo de seguridad. Atalaya vigila el correo de todos los buzones, explica en español por qué desconfía de un mensaje y deja la decisión a una persona. Esto es una demostración con 14 buzones simulados: no hay correos reales.»

### 2 · Una campaña (0:25–0:50)
**Pantalla:** el banner **«1 campaña en 2 buzones»**; mostrar las pestañas **Todos / Alta / Media / Baja / Limpios / Cuarentena / Legítimos** (pasar el cursor por ellas).
**Voz:** «El mismo ataque llegó a dos personas. Atalaya lo agrupa como una campaña. Las pestañas reparten los correos sin repetirlos, y sus números suman el total.»

### 3 · Una alerta (0:50–1:20)
**Pantalla:** abrir una alerta alta → **Ficha técnica** (SPF/DKIM/DMARC, IP de origen, vector de ataque, enlace neutralizado) → pestaña **Análisis forense**.
**Voz:** «Los hechos los calcula el código: autenticación del remitente, dominios parecidos, enlaces. La inteligencia artificial solo redacta la explicación, y **en esta demo la explicación es simulada**; la pantalla lo dice. [Si ya mediste la IA real, añade aquí una frase con el dato; si no, no la menciones.] Atalaya nunca guarda el asunto ni el contenido del correo.»

### 4 · Una persona decide (1:20–1:50)
**Pantalla:** pulsar **«Poner en cuarentena en los 2 buzones»** (la cuenta de la pestaña **Cuarentena** sube). Luego, en un correo que Atalaya **no** marcó como alto, intentar **«Poner en cuarentena»** y mostrar que pide un **motivo escrito**.
**Voz:** «Una sola acción aísla el ataque en los dos buzones. Es reversible: nada se borra ni se envía. Y si decides ir en contra de lo que Atalaya recomienda, tienes que explicar por qué; queda en el historial.»

### 5 · Supervisor y por área (1:50–2:15)
**Pantalla:** selector de **rol** (abajo a la izquierda) → **supervisor** → intentar una acción y mostrar el aviso «solo lectura». Después **Analítica y Tráfico** (por área) y **Historial de Amenazas** → **informe de la organización en PDF**.
**Voz:** «El supervisor lo ve todo, pero el servidor rechaza cualquier escritura: no solo se esconden los botones. Se analiza por área, no persona por persona, y cada decisión queda registrada. El informe se descarga en PDF.»

### 6 · Cierre y límites (2:15–2:35)
**Pantalla:** volver al **Panel de Control**; opcional, mostrar un segundo el README con el diagrama del kit.
**Voz:** «Atalaya se instala dentro de cada organización: su correo no pasa por nosotros. Hoy funciona con Gmail y Google Workspace, no analiza adjuntos ni la reputación de los enlaces, y la medición con 62 correos sintéticos detectó 27 de 30 intentos. Es una hipótesis de negocio, sin clientes todavía. El código y la guía están en el repositorio.»

## Versión corta (60 s) si el formulario lo exige
Tomas 0 + 1 (acortada) + 4 + 6 (solo la primera y la última frase).

## Tomas opcionales (solo si hay tiempo y funcionan al ensayar)
- **IA real:** si recargas la API y la prueba sale bien, graba **aparte** una toma corta con la explicación real de un correo y el costo medido. Solo entonces cambia la frase de la toma 3. **No la incluyas si no se probó.**
- **Instalador del kit:** grabar el asistente `tools/kit/instalar` en un terminal hasta la verificación previa, **sin datos reales de Google**. No digas que se probó con Workspace: no es cierto. Ver [INSTALACION.md](INSTALACION.md).

## Qué NO decir ni mostrar
- Que la IA real ya funciona, **hasta medirla**.
- Que hay clientes, entrevistas o resultados de la encuesta (hoy: 0 entrevistas).
- Que el kit se probó con una organización de Workspace real (no se probó).
- Precio ni ingresos: el precio está sin definir.
- Datos personales, tu correo, claves o el soporte de GitHub.

## Si algo falla en la grabación
- La demo tarda o da 503: espera 1 minuto y recarga. Si sigue, usa los datos locales (`uvicorn app.main:app`, modo demo por defecto).
- Un botón se llama distinto: di lo que ves, y corrige después este guion.
- «Reiniciar demostración» restaura los datos si algo quedó a medias.

## Después
- [ ] Subir el video (YouTube **no listado** o Drive con enlace) y **probar el enlace en una ventana privada**, sin sesión.
- [ ] Poner el enlace en el campo de video de la entrega y en [CHECKLIST_ENTREGA.md](CHECKLIST_ENTREGA.md).

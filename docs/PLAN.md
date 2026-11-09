# Plan de trabajo — HuelaEstafa Guard

Hoy: 8 nov. Hackathon: 20–22 nov. Entrega: **domingo 22**. Trabajo en solitario.

## Antes del evento (8–19 nov)
- [ ] Inscribirse en Dojo (el encuentro del viernes 20 en WeWork Costa Rica es aparte).
- [ ] Confirmar temática, criterios de jurado y si se permite código previo.
- [ ] **Leer las reglas del hackathon sobre datos de terceros y uso de APIs** (ver `ETICA_LEGAL_SEGURIDAD.md`).
- [ ] Crear en Google Cloud un proyecto de prueba: pantalla de consentimiento en modo "Testing", agregar tus cuentas de prueba como usuarios de prueba, habilitar Gmail API.
- [ ] Crear **2–3 cuentas Gmail propias de prueba** (una "víctima", otra "atacante"). Nunca usar cuentas ajenas.
- [ ] Probar el flujo OAuth básico (login + listar 5 correos) con una cuenta propia.
- [ ] Conseguir claves: Claude, Safe Browsing, VirusTotal (plan gratuito, con límites).
- [ ] Preparar 20–30 correos de prueba (phishing simulado inofensivo + legítimos). Adjuntos: solo archivo de prueba EICAR.
- [ ] Entorno: `python -m venv .venv`, `pip install fastapi uvicorn anthropic tldextract httpx google-auth-oauthlib google-api-python-client cryptography`.
- [ ] Cuenta en Render/Railway (HTTPS para la redirección de OAuth).

## Viernes 20 — Conexión y núcleo
- [ ] Login con Google + consentimiento visible; guardar tokens **cifrados**.
- [ ] Lectura de correos nuevos cada minuto (`history.list`).
- [ ] Analizador base: SPF/DKIM/DMARC, dominio parecido, remitente vs. respuesta, acortadores.
- [ ] **Corte a las ~4 h:** si OAuth no funciona, pasar al Plan B (entrada manual).

## Sábado 21 — IA, panel y seguridad
- [ ] Reputación de enlaces y hash de adjuntos.
- [ ] Explicación con Claude en JSON; el correo va como dato, nunca como instrucción.
- [ ] Etiqueta "Sospechoso" en Gmail (permiso `gmail.modify`; si da problemas, solo panel).
- [ ] Panel de alertas (sin contenido de correos).
- [ ] Pruebas de prompt injection y de límites de las APIs.

## Domingo 22 — Entrega
- [ ] Pulir, manejo de errores, datos de demo.
- [ ] Deploy y prueba del link público.
- [ ] Grabar demo de respaldo (2–3 min) y escribir la descripción.
- [ ] Publicar en Dojo antes del cierre.

## MVP mínimo
Login con Google → leer correos nuevos → analizar → alerta en panel. Lo demás son extras.

## Reglas
- `git init` al empezar; **nunca** subir claves, tokens ni `client_secret.json` (usar `.gitignore` y variables de entorno).
- Sin funciones nuevas después del domingo al mediodía.
- Siempre una versión desplegada que funcione.

## Contexto: participación virtual desde Panamá
- [ ] Confirmar con Dojo que podés participar en línea desde Panamá, y si hay requisitos de elegibilidad por país.
- [ ] Preguntar si los **premios** tienen restricciones para quienes no residen en Costa Rica (entrega, pago, impuestos).
- [ ] **Hora límite:** domingo 22, 11:59 p. m. hora de Costa Rica = **12:59 a. m. del lunes 23 en Panamá**. Meta propia: entregar antes de las **10:00 p. m. (Panamá)** del domingo. Inicio: viernes 20, 10:00 a. m. (Panamá).
- [ ] Elegir track (recomendado: **02 AI Operators**, ver `docs/REGLAS_Y_TRACKS.md`) y confirmar con Dojo si se puede entrar a ambos.
- [ ] Crear `docs/USO_DE_IA.md` (herramientas, para qué, ejemplos de prompts): la entrega exige explicar cómo usaste AI coding.
- [ ] Si hacés pruebas antes del 20, registrarlas en `docs/ESTADO_INICIAL.md` (el trabajo previo debe distinguirse del avance del 20-22).
- [ ] Preguntar cómo se conectará lo virtual con el encuentro del viernes 20 (¿transmisión, canal de chat, mentorías en línea?).
- [ ] Verificar internet estable y un plan B de conexión (datos móviles) para el día de la entrega y la demo.
- [ ] Local: adaptar la lista de marcas y estafas también a Panamá (bancos locales, apps de pago como Yappy, entidades públicas). Verificá nombres reales antes de usarlos.

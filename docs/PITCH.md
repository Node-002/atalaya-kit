# Guion del pitch (2–3 min)

> Borrador para que la persona autora lo revise y lo adapte a su voz. Todo lo que se afirma existe hoy en el repositorio. Las cifras externas vienen de [EVIDENCIA_PUBLICA.md](EVIDENCIA_PUBLICA.md) y **hay que abrir cada fuente antes de decirlas en voz alta** (esta redacción no las reabrió). Demo pública: `https://atalaya-demo.onrender.com`.

**Mensaje central (una frase):** *Atalaya vigila el correo de toda una organización pequeña, explica en español por qué desconfía y deja la decisión final a una persona, sin guardar el contenido de los correos. Se instala dentro de cada organización: tu correo no pasa por nosotros.*

## Estructura por criterios del jurado
| Parte | Criterio | Tiempo | Qué debe quedar claro |
|---|---|---|---|
| 1. Problema | Problema (30 %) | 0:00–0:35 | Quién sufre, cuánto duele (con fuente y advertencia) y por qué las soluciones actuales no le sirven |
| 2. Demo | Demo real (25 %) | 0:35–1:55 | Funciona en vivo, sin cuenta, y hace algo difícil de hacer a mano: aislar un ataque en varios buzones |
| 3. Negocio | Negocio (25 %) | 1:55–2:25 | Quién paga, cómo (hipótesis marcada como tal), por qué se instala en cada organización (kit autoalojado) y la hoja de ruta |
| 4. Experiencia | Experiencia (20 %) | repartido en la demo + 2:25–2:45 | Español sencillo, motivo obligatorio, supervisor de solo lectura, accesibilidad |
| 5. Límites y cierre | Honestidad | 2:45–3:00 | Qué no hace todavía |

## Guion
### 1. Problema (35 s)
> «Casi todos los ataques empiezan con un correo. Un colegio, una clínica o una pyme con 5 a 100 buzones no tiene un equipo de seguridad: depende de que cada persona dude a tiempo. Según estudios que citan Kaspersky y ESET, el phishing es de los ataques más reportados por las pymes de la región. Esas cifras vienen de empresas que venden seguridad y miden cosas distintas, así que las uso como contexto, no como prueba. Las soluciones que existen vienen de grandes proveedores pensados para equipos de TI.»

*Mostrar:* una diapositiva con una o dos cifras, cada una con su fuente en pantalla. Detalle y advertencias en [NEGOCIO_RESUMEN.md](NEGOCIO_RESUMEN.md).

### 2. Demo (80 s) — recorrido paso a paso
Abrir la demo **unos minutos antes** (el plan gratuito se duerme y la primera carga puede tardar ~1 min). Cada visitante recibe **su propia copia** de los datos, así que lo que haga no afecta a otras personas; «Reiniciar demostración» la restaura.

| Tiempo | Paso | Qué decir |
|---|---|---|
| 0:35 | Abrir la demo en ventana privada: **Panel de Control** con las cuatro tarjetas (correos analizados y amenazas altas, medias y bajas), «Vigilancia activa · 14 buzones» y el aviso «Demostración con datos simulados» | «Esto es una organización con 14 buzones. Son empleados simulados: no hay correos reales.» |
| 0:50 | Banner **«1 campaña en 2 buzones»** y la lista con las pestañas Todos / Alta / Media / Baja / Cuarentena / Legítimos | «El mismo ataque llegó a dos personas. Atalaya lo agrupa como una campaña.» |
| 1:00 | Abrir una alerta: **Ficha técnica** (autenticación SPF/DKIM/DMARC, IP de origen, vector de ataque, Return-Path enmascarado, enlace neutralizado) y la pestaña **Análisis forense** («¿Por qué Atalaya detectó esta amenaza?») | «Los hechos los calcula el código, no la IA. La explicación en la demo es **simulada** y la pantalla lo dice. Los datos técnicos salen de las cabeceras: nunca guardo el asunto ni el contenido.» |
| 1:15 | Pulsar **Poner en cuarentena en los 2 buzones** | «Una acción aísla el ataque en todos los buzones. Es reversible: nada se borra ni se envía.» |
| 1:30 | En un correo que Atalaya no marcó como riesgo alto, pulsar «Poner en cuarentena» (o «Es legítimo» en uno marcado) → pide **motivo escrito** | «Si decides ir en contra de Atalaya, tienes que explicar por qué. Queda en el historial.» |
| 1:40 | Selector de **rol** (abajo a la izquierda) → **supervisor**; intentar una acción | «El supervisor ve todo pero el servidor rechaza cualquier escritura. No solo se esconden botones.» |
| 1:48 | **Analítica y Tráfico** (por área) y **Historial de Amenazas** → **informe de la organización en PDF** | «Se analiza por área, no persona por persona. Cada decisión queda con quién y cuándo, y el informe se descarga en PDF.» |

> Antes de grabar o presentar, ensayar el recorrido completo y confirmar los nombres exactos de los botones en la demo desplegada (el diseño cambió el 21 nov). Si la demo falla: video de respaldo (si se graba) o capturas. No improvisar con Google en vivo.

### 3. Negocio (35 s)
> «Atalaya **se instala dentro de cada organización**: es un kit autoalojado, con su propia aplicación de Google marcada como interna. Su correo no pasa por nosotros y no tenemos que custodiar sus claves, que era el obstáculo de ofrecerlo como servicio. Se vende la licencia del software: el código es AGPL-3.0 y hay una licencia comercial para quien lo quiera usar en un producto cerrado. **Es una hipótesis**: no tengo clientes ni entrevistas hechas [ajustar si cambia], el precio no está definido y el costo de la IA por correo **todavía no lo medí** [actualizar si se mide]. La hoja de ruta: Gmail y Google Workspace hoy, Microsoft 365 después con el mismo modelo, y un servicio alojado cuando Google verifique la aplicación. Frente a Proofpoint, Abnormal o Defender para Office 365, Atalaya apuesta por el español, la explicación visible y la privacidad por diseño; no promete detectar más que ellos.»

*Mostrar:* el diagrama `img/modelo-kit.png` (servicio alojado frente a kit) y la hoja de ruta en una línea.

*Detalle y riesgos:* [NEGOCIO_RESUMEN.md](NEGOCIO_RESUMEN.md), [MARKETPLACE_FICHA.md](MARKETPLACE_FICHA.md), [ADR 0012](adr/0012-kit-autoalojado-en-lugar-de-servicio-alojado.md), [COMPETENCIA.md](COMPETENCIA.md).

### 4. Experiencia (20 s, en la demo y aquí)
> «Todo en español sencillo, pensado para teclado y lectores de pantalla: Lighthouse de accesibilidad 100 y cero violaciones con axe en todas las vistas, según [INFORME_UI_FASE1B.md](INFORME_UI_FASE1B.md). Una persona siempre decide, y el correo se trata como dato hostil: la IA no tiene herramientas y su salida se valida.»

### 5. Límites honestos y cierre (20 s)
> «Lo que Atalaya no hace hoy: no analiza adjuntos ni la reputación de los enlaces, y solo funciona con Gmail y Google Workspace. La explicación con IA real está implementada pero [no la he probado con saldo / la probé y cuesta X por correo; ajustar]. Mi medición usa 62 correos sintéticos que escribí yo: detectó 27 de 30 intentos y marcó de más 3 de 32 correos legítimos; no es una medición con correos reales. El kit se construye y se prueba en el CI, pero **no lo verifiqué con una organización de Workspace real**. Atalaya: el agente que vigila el correo de tu organización.»

## Límites honestos (decirlos, no esconderlos)
- **Sin adjuntos ni reputación de enlaces** (Safe Browsing, VirusTotal): no están construidos.
- **Sin Microsoft 365:** hoy solo Gmail y Google Workspace. Está en la hoja de ruta con el mismo modelo de instalación por organización (ADR 0012); no está construido ni probado.
- **IA real:** está implementada (`AnthropicExplainer`) y [actualizar: no se ha corrido con saldo / se probó y costó X por correo]. En la demo pública la explicación es simulada y la pantalla lo dice.
- **Corpus sintético:** 62 correos escritos por el propio desarrollador (30 intentos y 32 legítimos); 27/30 intentos detectados y 3/32 legítimos marcados de más ([RESULTADOS_PRUEBAS.md](RESULTADOS_PRUEBAS.md)). Parte de la mejora viene de casos escritos para funciones nuevas: **no es rendimiento real**.
- **Sin señales técnicas, no hay detección:** un «jefe» que pide una transferencia sin enlaces pasa.
- **El kit no se verificó con una organización de Workspace real:** el CI construye la imagen, comprueba que se niega a arrancar sin claves y que levanta con claves falsas, y el modo Gmail se probó a mano con cuentas de prueba. Los pasos de Google Cloud de la guía no se ejecutaron con una organización real.
- **Google en modo de pruebas** para la cuenta de prueba (máx. 100 usuarios, tokens de 7 días); una organización con su propia aplicación «interna» no tiene ese tope, según la documentación de Google (sin verificar con una organización real).
- **Sin clientes ni entrevistas** (salvo que la encuesta o entrevistas cambien esto antes de entregar; en ese caso, decir el número exacto, sin redondear).
- **Dominios de marcas:** se verificaron con fuentes públicas el 21 nov ([VERIFICACION_MARCAS.md](VERIFICACION_MARCAS.md)); algunos quedaron «sin confirmar» y la lista debe revisarse con el tiempo.
- **Seguridad:** hubo una prueba de intrusión propia contra la demo (un fallo alto, corregido) y herramientas de análisis, siempre contra el propio equipo; no hay revisión independiente.
- **Privacidad:** además del veredicto, las señales, el hash y el estado, guarda metadatos técnicos de cabeceras (resultado SPF/DKIM/DMARC, IP de origen, dominios de respuesta y de enlaces); nunca asunto, cuerpo ni adjuntos.

## Preguntas probables del jurado
| Pregunta | Respuesta honesta |
|---|---|
| ¿Por qué no usar la protección de Google o Microsoft? | Existe y es buena; Atalaya no promete detectar más. Aporta explicación en español, visión por organización y campañas. No se ha comparado con ellas. |
| ¿Quién paga y cuánto? | Hipótesis: la organización, por buzón. Sin validar. |
| ¿Qué pasa con la privacidad? | No guarda cuerpos ni adjuntos; guarda veredicto, señales, hash y estado, cifrado. Si se activa la IA, recibiría texto enmascarado y recortado. Ver [POLITICA_PRIVACIDAD.md](POLITICA_PRIVACIDAD.md). |
| ¿Es una demo real? | Son reales el código y el recorrido; los correos y empleados son simulados y la explicación es simulada. El modo Gmail existe y se probó solo en local con una cuenta de prueba. |
| ¿La IA puede ser manipulada por un correo? | El correo va delimitado como dato, la IA no tiene herramientas, la salida se valida y **no puede bajar el riesgo**. Probado con explicador simulado, nunca con IA real. |
| ¿Por qué un kit instalable y no un servicio en la nube? | Para ofrecer un servicio con Gmail, Google exige verificar la aplicación y una auditoría de seguridad, y yo tendría que custodiar los correos de todos. Con el kit, cada organización usa su propia aplicación «interna» y sus propias claves: no veo sus datos. El servicio alojado queda para cuando Google verifique la app. |
| ¿Cómo ganas dinero si el código es abierto (AGPL)? | Vendo licencias comerciales a quien quiera usarlo en un producto cerrado, más soporte, instalación y, más adelante, el servicio alojado. La AGPL evita que alguien lo ofrezca como servicio cerrado sin publicar sus cambios. Es una hipótesis sin validar. |
| ¿Y Microsoft 365? | En la hoja de ruta: mismo modelo, con el registro de aplicación de cada organización. Hoy no está construido. |

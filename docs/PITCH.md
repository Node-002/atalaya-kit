# Guion del pitch (2–3 min)

> Borrador para que la persona autora lo revise y lo adapte a su voz. Todo lo que se afirma existe hoy en el repositorio. Las cifras externas vienen de [EVIDENCIA_PUBLICA.md](EVIDENCIA_PUBLICA.md) y **hay que abrir cada fuente antes de decirlas en voz alta** (esta redacción no las reabrió). Demo pública: `https://atalaya-demo.onrender.com`.

**Mensaje central (una frase):** *Atalaya vigila el correo de toda una organización pequeña, explica en español por qué desconfía y deja la decisión final a una persona, sin guardar el contenido de los correos.*

## Estructura por criterios del jurado
| Parte | Criterio | Tiempo | Qué debe quedar claro |
|---|---|---|---|
| 1. Problema | Problema (30 %) | 0:00–0:35 | Quién sufre, cuánto duele (con fuente y advertencia) y por qué las soluciones actuales no le sirven |
| 2. Demo | Demo real (25 %) | 0:35–1:55 | Funciona en vivo, sin cuenta, y hace algo difícil de hacer a mano: aislar un ataque en varios buzones |
| 3. Negocio | Negocio (25 %) | 1:55–2:25 | Quién paga, cómo (hipótesis marcada como tal) y por qué es defendible |
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
| 0:35 | Abrir la demo en ventana privada. Se ve la pestaña **Resumen**: tarjetas por buzón con cobertura y contadores, y el aviso «Demostración: no se conecta ningún correo real» | «Esto es una organización con varios buzones. Lo urgente va primero. Son empleados simulados: no hay correos reales.» |
| 0:50 | Pestaña **Correos**: aparece «1 campaña en 2 buzones» y las alertas agrupadas | «El mismo ataque llegó a dos personas. Atalaya lo agrupa como una campaña.» |
| 1:00 | Abrir una alerta: señales (autenticación del remitente, dominio parecido a una marca, enlace acortado…) y la explicación | «Los hechos los calcula el código, no la IA. La explicación en la demo es **simulada** y la pantalla lo dice.» |
| 1:15 | Pulsar **Poner en cuarentena en los 2 buzones** | «Una acción aísla el ataque en todos los buzones. Es reversible: nada se borra ni se envía.» |
| 1:30 | En un correo que Atalaya no marcó como riesgo alto, pulsar «Poner en cuarentena» (o «Es legítimo» en uno marcado) → pide **motivo escrito** | «Si decides ir en contra de Atalaya, tienes que explicar por qué. Queda en el historial.» |
| 1:40 | Botón de rol → **supervisor**; intentar una acción | «El supervisor ve el panel, el historial y los informes, pero el servidor rechaza cualquier escritura. No solo se esconden botones.» |
| 1:48 | Pestaña **Historial** → **Ver reporte de la organización** (informe por correo) | «Cada decisión queda con quién y cuándo. Hay un informe de la organización.» |

> Antes de grabar o presentar, ensayar el recorrido completo y confirmar los nombres exactos de botones en la demo desplegada. Si la demo falla: video de respaldo (si se graba) o capturas. No improvisar con Google en vivo.

### 3. Negocio (30 s)
> «Quien paga es la organización, por buzón protegido al mes. **Es una hipótesis**: no tengo clientes ni entrevistas hechas [ajustar si cambia], y el precio es una estimación sin validar. Los costos principales serán la IA por correo analizado, que **todavía no medí con IA real**, y el trabajo de verificación de Google. Frente a Proofpoint, Abnormal o Defender para Office 365, Atalaya apuesta por español, explicación de cada veredicto y privacidad por diseño. No digo que detecte más que ellos.»

*Detalle y riesgos:* [NEGOCIO_RESUMEN.md](NEGOCIO_RESUMEN.md), [COMPETENCIA.md](COMPETENCIA.md).

### 4. Experiencia (20 s, en la demo y aquí)
> «Todo en español sencillo, sin jerga, pensado para teclado y lectores de pantalla (Lighthouse de accesibilidad 100 en la demo, según [INFORME_ENDURECIMIENTO_21_NOV.md](INFORME_ENDURECIMIENTO_21_NOV.md)). Una persona siempre decide, y el correo se trata como dato hostil: la IA no tiene herramientas y su salida se valida.»

### 5. Límites honestos y cierre (15 s)
> «Lo que Atalaya no hace hoy: no analiza adjuntos ni la reputación de los enlaces, solo funciona con Gmail, y la explicación con IA real está implementada pero no la he probado con saldo. Mi medición usa 48 correos sintéticos que escribí yo: detectó 21 de 24 intentos y marcó de más 3 de 24 correos legítimos; no es una medición con correos reales. Atalaya: el agente que vigila el correo de tu organización.»

## Límites honestos (decirlos, no esconderlos)
- **Sin adjuntos ni reputación de enlaces** (Safe Browsing, VirusTotal): no están construidos.
- **Sin Microsoft 365:** solo Gmail.
- **IA real sin probar con saldo:** está implementada (`AnthropicExplainer`), pero no se ha corrido; no se midió costo por correo ni efecto en la detección. En la demo la explicación es simulada.
- **Corpus sintético:** 48 correos escritos por el propio desarrollador; 21/24 intentos detectados y 3/24 legítimos marcados de más ([RESULTADOS_PRUEBAS.md](RESULTADOS_PRUEBAS.md)). La mejora de 11/24 a 21/24 viene de casos escritos para la función nueva: **no es rendimiento real**.
- **Sin señales técnicas, no hay detección:** un «jefe» que pide una transferencia sin enlaces pasa.
- **Google en modo de pruebas:** máximo 100 usuarios de prueba y tokens que caducan a los 7 días hasta verificar la aplicación.
- **Sin clientes ni entrevistas** (salvo que la encuesta o entrevistas cambien esto antes de entregar; en ese caso, decir el número exacto, sin redondear).
- **Los dominios oficiales de las marcas están escritos de memoria** y sin verificar.
- Sin prueba de intrusión independiente; las herramientas de seguridad se usaron solo contra el propio equipo.

## Preguntas probables del jurado
| Pregunta | Respuesta honesta |
|---|---|
| ¿Por qué no usar la protección de Google o Microsoft? | Existe y es buena; Atalaya no promete detectar más. Aporta explicación en español, visión por organización y campañas. No se ha comparado con ellas. |
| ¿Quién paga y cuánto? | Hipótesis: la organización, por buzón. Sin validar. |
| ¿Qué pasa con la privacidad? | No guarda cuerpos ni adjuntos; guarda veredicto, señales, hash y estado, cifrado. Si se activa la IA, recibiría texto enmascarado y recortado. Ver [POLITICA_PRIVACIDAD.md](POLITICA_PRIVACIDAD.md). |
| ¿Es una demo real? | Son reales el código y el recorrido; los correos y empleados son simulados y la explicación es simulada. El modo Gmail existe y se probó solo en local con una cuenta de prueba. |
| ¿La IA puede ser manipulada por un correo? | El correo va delimitado como dato, la IA no tiene herramientas, la salida se valida y **no puede bajar el riesgo**. Probado con explicador simulado, nunca con IA real. |

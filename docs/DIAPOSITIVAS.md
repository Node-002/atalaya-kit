# Esquema de diapositivas (11)

> Solo el esquema; no hay archivos de diapositivas. La presentación debe tener **enlace público** (no archivo local). Guion completo en [PITCH.md](PITCH.md). Estilo sugerido: pocas palabras, una idea por lámina, capturas reales de la demo.
> Tiempo total objetivo: 2 a 3 minutos (las láminas 1 y 11 casi no consumen tiempo).

| # | Criterio | Título |
|---|---|---|
| 1 | — | Atalaya |
| 2–3 | Problema (30 %) | El problema · Por qué hoy no se resuelve |
| 4–6 | Demo real (25 %) | Cómo funciona · Demo · Una persona decide |
| 7–9 | Negocio (25 %) | A quién se vende · Una instalación por organización · Modelo, competencia y hoja de ruta |
| 10 | Honestidad | Límites honestos |
| 11 | — | Cierre y enlaces |

---
## 1. Atalaya — el agente que vigila el correo de tu organización
- Revisa cada correo nuevo, explica en español por qué desconfía y pide aprobación humana para lo crítico.
- Equipo Atalaya (una persona) · Dojo AI Hackathon · Build for Business.
- **Mostrar:** logo/escudo y nombre. Nada más.
- **Notas:** 10 segundos. Frase de gancho: «Casi todo ataque empieza con un correo».

## 2. El problema
- Organizaciones de 5 a 100 buzones (colegios, clínicas, pymes, universidades) sin equipo de seguridad.
- Según Kaspersky, 43 % de las pymes de LATAM sufrió phishing el año anterior; ESET: 73 % de las **empresas** fue objetivo en 2025 (distintos estudios, distintas preguntas).
- **Mostrar:** las cifras con fuente y año en pantalla, y la advertencia «estudios de proveedores de seguridad».
- **Notas:** abrir cada fuente antes ([EVIDENCIA_PUBLICA.md](EVIDENCIA_PUBLICA.md)). No mezclar ambas cifras. No decir «ataques exitosos» a partir de intentos (el «500 %» de la AIG son intentos). No decir que los clientes potenciales tienen el problema: eso no está validado.

## 3. Por qué hoy no se resuelve
- Las soluciones fuertes (pasarelas, seguridad por API) vienen de grandes proveedores, pensadas para equipos de TI, en inglés.
- Muchas dicen «bloqueado» sin explicar por qué.
- **Mostrar:** tabla corta de tipos de competidor ([COMPETENCIA.md](COMPETENCIA.md)).
- **Notas:** esa tabla es de conocimiento general **sin verificación en vivo**: revisar sitios oficiales antes de nombrar funciones o precios. No prometer detectar más que Google o Microsoft.

## 4. Cómo funciona
- Reglas calculadas por código: SPF/DKIM/DMARC, dominios parecidos y homógrafos (28 marcas con dominios verificados en fuentes públicas), «responder a» distinto, enlaces acortados, urgencia, instrucciones ocultas a una IA.
- La IA solo redacta la explicación; el correo es dato hostil y la salida se valida.
- No guarda cuerpos ni adjuntos: solo veredicto, señales, hash, estado y metadatos técnicos de cabeceras (SPF/DKIM/DMARC, IP de origen, dominios de respuesta y de enlaces); todo cifrado.
- **Mostrar:** el diagrama de flujo del README (Gmail → enmascarado → reglas → explicación → panel → decisión humana).
- **Notas:** en la demo la explicación es simulada. La IA real [no se ha probado con saldo / se probó: ajustar].

## 5. Demo en vivo (80 s)
- Panel de Control con cuatro tarjetas → «1 campaña en 2 buzones» → una acción aísla el ataque en ambos.
- Una alerta abierta: ficha técnica, análisis forense y cabeceras → motivo obligatorio si vas contra Atalaya → supervisor de solo lectura → Analítica y Tráfico por área → informe de la organización en PDF.
- **Mostrar:** la demo `https://atalaya-demo.onrender.com` en vivo (tener capturas de respaldo en la lámina de reserva).
- **Notas:** recorrido con tiempos en [PITCH.md](PITCH.md). Abrir la demo antes: el plan gratuito se duerme. Cada visitante tiene su propia copia.

## 6. Una persona decide
- Cuarentena = sacar de la bandeja + etiqueta «Sospechoso»; reversible; nunca borra ni envía.
- Cada decisión queda con quién y cuándo (historial).
- Español sencillo, teclado y lectores de pantalla (Lighthouse de accesibilidad 100 en la demo).
- **Mostrar:** captura del diálogo «Motivo de tu decisión» y del historial.
- **Notas:** cubre el criterio de experiencia (20 %). Decir que el supervisor está bloqueado en el servidor (403), no solo en botones.

## 7. A quién se vende
- Organizaciones de 5 a 100 buzones con Google Workspace (colegios, clínicas, pymes, universidades de Panamá y la región). Paga la persona responsable de TI o la dirección; usuario final: cada empleado.
- **Mostrar:** una sola frase y los cuatro tipos de cliente.
- **Notas:** **sin clientes ni entrevistas**: es una hipótesis. Si llegan respuestas de la encuesta, poner el número exacto y decir que la muestra es pequeña y no representativa.

## 8. Una instalación por organización (kit autoalojado)
- Cada organización instala **su propia copia**, con su propia aplicación de Google «interna» y sus propias claves: su correo no pasa por nosotros.
- Se evita la verificación de Google (que exige un servicio que custodia correos de terceros) y nosotros no guardamos datos de nadie.
- Se entrega el software, una guía de instalación (español e inglés, con evaluación en 15 minutos) y la licencia.
- **Mostrar:** el diagrama `img/modelo-kit.png` (servicio alojado frente a kit).
- **Notas:** decir que el kit se construye y se prueba en el CI, pero que los pasos de Google Cloud **no se verificaron con una organización Workspace real**. Detalle en [ADR 0012](adr/0012-kit-autoalojado-en-lugar-de-servicio-alojado.md) y [INSTALACION.md](INSTALACION.md).

## 9. Modelo, competencia y hoja de ruta (hipótesis)
- Licencia del kit por organización (hipótesis; **precio sin definir**); código AGPL-3.0 y licencia comercial para productos cerrados; soporte e instalación como servicio.
- Costos: IA por correo (sin medir hasta probar con saldo), soporte, mantenimiento. Alojamiento: lo pone cada cliente.
- Competencia: Google/Microsoft incluidos, pasarelas y seguridad por API (en inglés, pensadas para equipos de TI). Diferencia: español, explicación visible, privacidad por diseño, instalación en la propia infraestructura. No «detecta más».
- Hoja de ruta: **hoy** kit para Gmail/Google Workspace → **después** Microsoft 365 con el mismo modelo → **más adelante** servicio alojado, cuando Google verifique la aplicación.
- **Mostrar:** etiqueta grande «HIPÓTESIS» y la hoja de ruta en tres pasos.
- **Notas:** el cobro y la entrega en el Marketplace de Dojo siguen sin respuesta por escrito ([PREGUNTAS_ORGANIZADORES.md](PREGUNTAS_ORGANIZADORES.md)). Ficha del producto en [MARKETPLACE_FICHA.md](MARKETPLACE_FICHA.md).

## 10. Límites honestos
- Sin adjuntos ni reputación de enlaces · solo Gmail/Workspace (Microsoft 365 en la hoja de ruta).
- IA real: [sin probar con saldo / probada: ajustar] · el kit no se verificó con una organización Workspace real.
- Medición con 62 correos **sintéticos**: 27/30 intentos detectados, 3/32 legítimos marcados de más.
- **Mostrar:** lista corta, sin disculpas.
- **Notas:** decirlo con calma; la honestidad es parte del producto. Aclarar que parte de la mejora en la medición viene de casos escritos para las funciones nuevas.

## 11. Cierre y enlaces
- Demo: `https://atalaya-demo.onrender.com` · Repositorio · Encuesta.
- «Atalaya: el agente que vigila el correo de tu organización, y se instala en tu organización.»
- **Mostrar:** enlaces cortos/QR. Incluir el enlace al repositorio solo cuando esté público.
- **Notas:** probar cada enlace en ventana privada antes ([CHECKLIST_ENTREGA.md](CHECKLIST_ENTREGA.md)).

---
## Reserva (no se muestra salvo pregunta)
- **R1. Capturas de la demo** (Resumen, campaña, diálogo de motivo, historial) por si falla la conexión.
- **R2. Seguridad:** 512 pruebas pasan; ruff, bandit, pip-audit y gitleaks limpios; el CI construye y escanea la imagen y prueba el kit; prueba de intrusión propia, ZAP, ffuf, Nmap, Trivy y Lighthouse solo contra el propio equipo ([INFORME_ENDURECIMIENTO_21_NOV.md](INFORME_ENDURECIMIENTO_21_NOV.md), [INFORME_PENTEST_DEMO_21_NOV.md](INFORME_PENTEST_DEMO_21_NOV.md)).
- **R3. Cómo se usó la IA para programar:** [USO_DE_IA.md](USO_DE_IA.md).

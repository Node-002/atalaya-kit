# Esquema de diapositivas (10)

> Solo el esquema; no hay archivos de diapositivas. La presentación debe tener **enlace público** (no archivo local). Guion completo en [PITCH.md](PITCH.md). Estilo sugerido: pocas palabras, una idea por lámina, capturas reales de la demo.
> Tiempo total objetivo: 2 a 3 minutos (las láminas 1 y 10 casi no consumen tiempo).

| # | Criterio | Título |
|---|---|---|
| 1 | — | Atalaya |
| 2–3 | Problema (30 %) | El problema · Por qué hoy no se resuelve |
| 4–6 | Demo real (25 %) | Cómo funciona · Demo · Una persona decide |
| 7–8 | Negocio (25 %) | A quién se vende · Modelo y competencia |
| 9 | Honestidad | Límites honestos |
| 10 | — | Cierre y enlaces |

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
- Reglas calculadas por código: SPF/DKIM/DMARC, dominios parecidos y homógrafos (22 marcas), «responder a» distinto, enlaces acortados, urgencia, instrucciones ocultas a una IA.
- La IA solo redacta la explicación; el correo es dato hostil y la salida se valida.
- No guarda cuerpos ni adjuntos: solo veredicto, señales, hash y estado; tokens cifrados.
- **Mostrar:** el diagrama de flujo del README (Gmail → enmascarado → reglas → explicación → panel → decisión humana).
- **Notas:** en la demo la explicación es simulada. La IA real no se ha probado con saldo.

## 5. Demo en vivo (80 s)
- Resumen por buzón → campaña «1 campaña en 2 buzones» → una acción aísla el ataque en ambos.
- Motivo obligatorio si vas contra Atalaya · supervisor de solo lectura · informe de la organización.
- **Mostrar:** la demo `https://atalaya-demo.onrender.com` en vivo (tener capturas de respaldo en la lámina siguiente de reserva).
- **Notas:** recorrido con tiempos en [PITCH.md](PITCH.md). Abrir la demo antes: el plan gratuito se duerme. Cada visitante tiene su propia copia.

## 6. Una persona decide
- Cuarentena = sacar de la bandeja + etiqueta «Sospechoso»; reversible; nunca borra ni envía.
- Cada decisión queda con quién y cuándo (historial).
- Español sencillo, teclado y lectores de pantalla (Lighthouse de accesibilidad 100 en la demo).
- **Mostrar:** captura del diálogo «Motivo de tu decisión» y del historial.
- **Notas:** cubre el criterio de experiencia (20 %). Decir que el supervisor está bloqueado en el servidor (403), no solo en botones.

## 7. A quién se vende
- Cliente que paga: la persona responsable de TI o la dirección de una organización pequeña; usuario final: cada empleado.
- Colegios, clínicas, pymes y universidades de Panamá y la región.
- **Mostrar:** una sola frase y los cuatro tipos de cliente.
- **Notas:** **sin clientes ni entrevistas**: es una hipótesis. Si llegan respuestas de la encuesta, poner el número exacto y decir que la muestra es pequeña y no representativa.

## 8. Modelo de ingresos y competencia (hipótesis)
- Suscripción mensual por buzón, con prueba gratuita. **Precio sin validar** (ver [NEGOCIO_RESUMEN.md](NEGOCIO_RESUMEN.md)).
- Costos principales: IA por correo (sin medir), verificación de Google, alojamiento y soporte.
- Diferencia: español, explicación visible, privacidad por diseño, instalación sencilla. No «detecta más».
- **Mostrar:** etiqueta grande «HIPÓTESIS» junto al modelo.
- **Notas:** mencionar caminos de venta en el Marketplace de Dojo sin afirmar cómo se cobra (pregunta abierta, ver [PREGUNTAS_ORGANIZADORES.md](PREGUNTAS_ORGANIZADORES.md)).

## 9. Límites honestos
- Sin adjuntos ni reputación de enlaces · solo Gmail (sin Microsoft 365).
- IA real sin probar con saldo · Google en modo de pruebas (máx. 100 usuarios).
- Medición con 48 correos **sintéticos**: 21/24 intentos detectados, 3/24 legítimos marcados de más.
- **Mostrar:** lista corta, sin disculpas.
- **Notas:** decirlo con calma; la honestidad es parte del producto. Aclarar que la mejora de 11/24 a 21/24 es de casos escritos para la función nueva.

## 10. Cierre y enlaces
- Demo: `https://atalaya-demo.onrender.com` · Repositorio · Encuesta.
- «Atalaya: el agente que vigila el correo de tu organización».
- **Mostrar:** enlaces cortos/QR. Incluir el enlace al repositorio solo cuando esté público.
- **Notas:** probar cada enlace en ventana privada antes ([CHECKLIST_ENTREGA.md](CHECKLIST_ENTREGA.md)).

---
## Reserva (no se muestra salvo pregunta)
- **R1. Capturas de la demo** (Resumen, campaña, diálogo de motivo, historial) por si falla la conexión.
- **R2. Seguridad:** 325 pruebas pasan; ruff, bandit, pip-audit y gitleaks limpios; ZAP, ffuf, Nmap, Trivy y Lighthouse solo contra el propio equipo ([INFORME_ENDURECIMIENTO_21_NOV.md](INFORME_ENDURECIMIENTO_21_NOV.md)).
- **R3. Cómo se usó la IA para programar:** [USO_DE_IA.md](USO_DE_IA.md).

# Cronograma — Atalaya (hora de Panamá, UTC−5)

> **Regla de oro:** el producto se construye a partir del **viernes 20, 10:00 a. m.** Antes de esa hora se permite **preparación** (entorno, cuentas, material de prueba, documentación y diseño en papel). **No se escribe código de la aplicación ni se crea su estructura antes de las 10:00.** Todo lo preparado se anota en `docs/ESTADO_INICIAL.md` con la hora.
> Dormir mínimo 6 horas por noche. Comer y descansar son parte del plan.

## Principio de trabajo: dos pistas en paralelo, con IA
| Pista | Qué incluye | Quién |
|---|---|---|
| **A: Núcleo** | Login de Google, lectura de correos, reglas de análisis, motor de decisión, etiquetas, pruebas | Vos, con IA como asistente (revisás todo el código) |
| **B: Interfaz y demo** | Panel, modo demo con bandeja simulada, textos en español, accesibilidad, luego el pitch | IA construye sobre datos de ejemplo; vos revisás y probás |

Las pistas se conectan por un **contrato de API** (formas JSON acordadas) definido el viernes por la mañana. Cada pista trabaja en su **rama de git** para no pisarse. El modo demo y la interfaz son el mismo trabajo: sirven a la vez para la nota de UX (20 %) y para la demo que los jueces pueden probar (25 %).

---

## Viernes 20 — antes del inicio (preparación)

| Hora | Qué hacer | Listo |
|---|---|:--:|
| 06:00–06:30 | Desayuno. Releer `docs/MVP_ALCANCE.md`, `docs/PLAN.md` y este cronograma. Confirmar con `git log` que el commit inicial existe y que `git status` está limpio. Abrir las reglas y la pestaña Tracks en Dojo. | ☐ |
| 06:30–07:30 | **Entorno:** `python -m venv .venv`, preparar herramientas (FastAPI, uvicorn, anthropic, cryptography, httpx, bandit, pip-audit, gitleaks). Confirmar que las claves estén **en variables de entorno** o en un `.env` fuera del repositorio. Probar internet y tener datos móviles de respaldo. | ☐ |
| 07:30–08:30 | **Consolas:** Google Cloud (proyecto en modo de pruebas, pantalla de consentimiento, usuarios de prueba, Gmail API habilitada). Si Microsoft es prioridad según las entrevistas, registro de aplicación en Entra. **Solo configuración, sin programar el login.** | ☐ |
| 08:30–09:30 | **Material de prueba:** los 30 correos (phishing simulado inofensivo y legítimos), lista de marcas de Panamá y Costa Rica. Cuentas Gmail de prueba. Escribir el **contrato de API** y el esquema de datos en `docs/` (diseño en papel). Actualizar `docs/ESTADO_INICIAL.md` con lo hecho y hacer commit solo de documentación. | ☐ |
| 09:30–09:45 | Pausa. Cerrar distracciones. Tener abiertos: terminal, editor, Dojo, esta página. | ☐ |
| 09:45 | Suena el recordatorio programado. Respirar y revisar el checklist de arranque. | ☐ |

## Viernes 20 — desde el inicio

| Hora | Pista A: núcleo | Pista B: interfaz y demo |
|---|---|---|
| **10:00–10:30** | **Arranque:** crear la rama de trabajo, la estructura `app/` y el commit "inicio del hackathon". Cargar `CLAUDE.md` con las reglas de trabajo (simple, cambios quirúrgicos, demostrar que funciona). | Misma sesión: acordar el contrato de API. |
| **10:30–13:30** | Login de Google + lectura de correos. **Hito: listar 5 correos.** | Panel y bandeja simulada con datos de ejemplo (IA). |
| **13:30–14:30** | Almuerzo y **punto de control:** ¿funciona el login? Si no, **corte duro a las 14:00 → Plan B** (entrada manual). | |
| **14:30–18:30** | Reglas: autenticación SPF/DKIM/DMARC, dominio parecido, remitente vs. respuesta, acortadores, urgencia. Pruebas automáticas sobre los 30 correos. | Pantallas de alertas y detalle. |
| 18:30–19:30 | Cena | |
| **19:30–22:30** | Motor de decisión y etiquetas en Gmail. **Hito: recorrido de punta a punta**, aunque se vea feo. | Conectar el panel con la API real. |
| 22:30–23:00 | Commit, completar `docs/USO_DE_IA.md`, anotar el plan de mañana. **Dormir.** | |

## Sábado 21

| Hora | Qué hacer |
|---|---|
| 07:30–08:00 | Repaso, revisar el estado, elegir lo más importante del día. |
| **08:00–12:00** | **Núcleo:** explicación con IA (el correo como dato hostil, datos enmascarados), aprobación humana y cuarentena, registro de auditoría, estado de cobertura. **Interfaz:** flujo de aprobación y estados. |
| **12:00** | **Corte de Microsoft:** si Gmail funciona de punta a punta, decidir si hay tiempo para un segundo conector. Si no, queda como siguiente paso. |
| 12:00–13:00 | Almuerzo |
| **13:00–17:00** | **Modo demo público** completo, textos en español sencillo, accesibilidad, pruebas de inyección de prompts. **Script de evaluación** que calcule aciertos y falsos positivos sobre los 30 correos. |
| **17:00–18:00** | **Revisión de seguridad:** gitleaks, bandit, pip-audit, Security Guidance. Corregir lo encontrado. |
| 18:00–19:00 | Cena |
| **19:00–22:00** | **Despliegue** (Render o Railway), aviso de privacidad visible, prueba del enlace público. Primer borrador de diapositivas con IA. |
| 22:00–23:00 | Borrador del video de demo. Commit. **Dormir.** |

## Domingo 22

| Hora | Qué hacer |
|---|---|
| 07:30–08:00 | Repaso y lista de lo que falta. |
| **08:00–12:00** | Pulir, corregir errores, pruebas completas del recorrido. Pasar las **citas y datos de las entrevistas** al pitch. Escaneo profundo con claude-security. |
| **12:00** | **Congelar funciones.** Desde aquí solo se corrige y se entrega. |
| 12:00–13:00 | Almuerzo |
| **13:00–16:00** | Pitch final con enlace público (Canva o Google Slides). Descripción, tecnologías y línea de la tarjeta en Dojo. |
| **16:00–18:00** | Grabar y subir el **video de 2 a 3 minutos** (YouTube, Loom o Vimeo). |
| 18:00–19:00 | Cena y revisión del checklist de entrega |
| **19:00–20:00** | Hacer el **repositorio público** (después de pasar gitleaks). Probar todos los enlaces en una ventana privada. |
| 20:00 | **Suena el recordatorio.** Cargar los enlaces en Dojo. |
| **21:30–22:00** | **Submit and publish.** Guardar una captura de la confirmación. |
| 22:00–00:59 | Margen de seguridad. El cierre oficial es a las 12:59 a. m. del lunes 23 (Panamá). |

---

## Si vas atrasado: qué se recorta, en este orden
1. Estado de cobertura ampliado
2. Registro de auditoría detallado
3. Conector de Microsoft
4. Reputación de enlaces (Safe Browsing) y hash de adjuntos
5. Mini lecciones y alertas por Telegram

**Lo que no se recorta nunca:** el recorrido completo, el modo demo, el pitch con datos del problema y del negocio, el video y el repositorio limpio.

## Qué se automatiza
| Qué | Cómo |
|---|---|
| Revisión de calidad y seguridad | Un script (`check`) que ejecute pruebas, bandit, pip-audit y gitleaks con un solo comando |
| Medición de detección | Script que corre los 30 correos y muestra aciertos y falsos positivos (sirve para el pitch) |
| Secretos | Revisión con gitleaks antes de cada commit |
| Despliegue | Despliegue automático del servicio al subir cambios |
| Revisión en GitHub | Acción de GitHub con las mismas comprobaciones, una vez que el repositorio sea público |
| Diapositivas | Generación de borrador desde el README y los resultados medidos |

## Checkpoints de decisión
| Hora | Pregunta | Si la respuesta es no |
|---|---|---|
| Vie 14:00 | ¿Funciona el login de Google? | Plan B: entrada manual del correo |
| Vie 22:30 | ¿Hay recorrido de punta a punta? | Recortar la lista anterior desde el punto 1 |
| Sáb 12:00 | ¿Gmail funciona completo? | No empezar Microsoft |
| Sáb 22:00 | ¿Hay enlace público funcionando? | Prioridad total al despliegue el domingo temprano |
| Dom 12:00 | ¿Funciones congeladas? | Solo se corrige; nada nuevo |
| Dom 21:30 | ¿Enlaces probados en ventana privada? | No pulsar Submit hasta tenerlo |

## Ajustes tras el kickoff (19 nov)
- **El video demo es opcional.** En el bloque del domingo 16:00–18:00, grabarlo solo si sobra tiempo; la prioridad pasa a la documentación y al pitch con enlace público.
- **Entregable obligatorio: repositorio + README + pitch deck.** Agregar al plan:
  - **Vie 10:00–10:45:** crear `PRD.md` (a partir de README y docs), `CLAUDE.md` y `docs/adr/0001-*.md` (primera decisión de arquitectura, por ejemplo la interfaz común de proveedores de correo). Son la evidencia del flujo con IA.
  - **Durante todo el hackathon:** una decisión de arquitectura por archivo en `docs/adr/`, con fecha.
  - **Sáb 17:00–18:00 y Dom 08:00–12:00:** README final con tres secciones: *Qué hace y para quién*, *Cómo correrlo* (probado en una máquina limpia o contenedor) y *Cómo usé agentic coding*.
  - **Dom 19:00–20:00:** probar el README desde cero siguiendo solo sus pasos.
- **Deadline sin prórroga:** domingo 22, 11:59 p. m. de Costa Rica (12:59 a. m. del lunes en Panamá). La meta de entrega sigue siendo las 10:00 p. m. de Panamá.
- **El "pricing" del listing:** definirlo el sábado con lo aprendido en las entrevistas (hipótesis razonada).

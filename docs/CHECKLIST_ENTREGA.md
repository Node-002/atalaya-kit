# Lista final antes de «Submit and publish»

> Meta propia: enviar **antes de las 10:00 p. m. (hora de Panamá) del domingo 22 nov**. Cierre oficial: 11:59 p. m. de Costa Rica (= 12:59 a. m. del lunes en Panamá), sin tiempo extra. Marcar cada casilla **solo después de probarla**. Actualizada el 22 nov 2026. Contexto: [CRONOGRAMA_SIGUIENTE.md](CRONOGRAMA_SIGUIENTE.md), [DESPLIEGUE.md](DESPLIEGUE.md).

## 0. Estado conocido (22 nov, madrugada)
| Punto | Estado |
|---|---|
| Demo pública en Render | Al día con el último commit de seguridad (error 422 genérico verificado) |
| Pruebas / ruff / bandit / pip-audit / Trivy / Semgrep | 569 pasan, 1 se omite; limpios ([INFORME_SEGURIDAD_FINAL_21_NOV.md](INFORME_SEGURIDAD_FINAL_21_NOV.md)) |
| CI de GitHub | En verde en el último push comprobado (tests, imagen Docker + Trivy, kit + instalador) |
| Licencia | AGPL-3.0 en `LICENSE`; licencia comercial = **borrador sin revisión legal** |
| IA real | **Sin probar** (espera de la recarga de la API) |
| Video | Dos versiones generadas (voz Margarita 2:21, voz Roberto 2:43) en `video/`, fuera de git; falta elegir y subir |
| Ticket al soporte de GitHub (purga de `refs/pull/*`) | **Sin respuesta**; las 7 referencias siguen en GitHub |
| Historial de la rama actual en GitHub | **Contiene un dato sensible en 9 commits antiguos** (versiones tempranas de `docs/AUDITORIA_PUBLICACION.md`); la punta está limpia. Ver sección 2 |
| Repositorio limpio (plan B) | **Creado el 22 nov como `Node-002/atalaya-kit`, privado** (una sola rama `hackathon/mvp`, sin pull requests ni etiquetas viejas): 0 coincidencias con las reglas reales, gitleaks limpio y todos los commits con la identidad `noreply`. **Falta hacerlo público** tras comprobar el CI. El repositorio anterior (`Node-002/atalaya`) sigue privado: no se renombró para no afectar el despliegue de Render |
| Respuestas de Dojo (sección 6) | Sin respuesta por escrito |

## 1. Decisión del repositorio (lo primero)
Los jueces deben poder abrirlo. **Antes de hacerlo público, el historial publicado tiene que estar limpio.**

| Plan | Cuándo | Qué implica |
|---|---|---|
| **A. Mismo repositorio** | Solo si GitHub purga las referencias **y** se reescribe otra vez la rama para quitar los 9 commits con el dato (nuevo `force-push`) | Dos pasos más con GitHub; el soporte tendría que incluir también los commits que el nuevo `force-push` deje sueltos |
| **B. Repositorio nuevo y limpio** (recomendado si no hay respuesta a media tarde) | GitHub no responde, o no se quiere esperar | Se crea un repositorio nuevo (sin pull requests ni referencias viejas) con el contenido de `C:\Hackaton-limpio`; el actual se renombra y se deja **privado** o se borra después |
| **C. Privado + jueces como colaboradores** | Solo si Dojo lo permite por escrito | Hay que preguntarlo (sección 6, #8) |

Pasos del plan B (cada uno es una acción hacia fuera: requiere tu visto bueno):
- [ ] Renombrar el repositorio actual (p. ej. `atalaya-archivo`), mantenerlo **privado**.
- [ ] Crear el repositorio nuevo **vacío** (sin README) con el nombre definitivo, **privado al principio**.
- [ ] Subir desde `C:\Hackaton-limpio`: `git remote add origin <URL nueva>` y `git push origin hackathon/mvp`.
- [ ] En GitHub: rama por defecto `hackathon/mvp`; comprobar que el **CI** corre en verde; activar Dependabot y alertas.
- [ ] `git ls-remote <URL nueva>`: solo debe existir `refs/heads/hackathon/mvp` (nada de `refs/pull/*`).
- [ ] Repetir `gitleaks detect --source .` y el verificador de reglas (`tools/historial/verificar_historial.py`) sobre el clon nuevo.
- [ ] Actualizar los enlaces en [DIAPOSITIVAS.md](DIAPOSITIVAS.md), el pitch, el video y el formulario de Dojo.
- [ ] Solo entonces, **hacer público** el repositorio nuevo.

## 2. Repositorio (comprobaciones)
- [ ] `gitleaks detect --source .` **sobre todo el historial** sin hallazgos (si hay uno, parar y avisar; **no** hacer público).
- [ ] Verificador **con las reglas reales** (las expresiones regulares, no solo texto literal): 0 coincidencias en **todos** los commits, no solo en la punta. *(El 22 nov se halló que comprobar solo la punta no bastaba.)*
- [ ] `pytest`, `ruff check .`, `bandit -q -r app -x app/tests` (con `PYTHONUTF8=1`) y `pip-audit` limpios.
- [ ] No hay en el repositorio `.env`, `secrets/`, `data/` ni `*.db` (`git ls-files`).
- [ ] **README** (ES y EN) coincide con lo que hace el código: cifras (28 marcas; 27/30 y 3/32 sobre 62 correos), kit autoalojado, límites. *Revisado el 22 nov.*
- [ ] Se ven las pruebas de evidencia: `CLAUDE.md`, `docs/adr/`, [USO_DE_IA.md](USO_DE_IA.md) y la descripción con un resumen.
- [ ] [POLITICA_PRIVACIDAD.md](POLITICA_PRIVACIDAD.md) y [TERMINOS_DE_USO.md](TERMINOS_DE_USO.md): se publican como **borrador con su advertencia**; el «Responsable» y el contacto quedan **[POR DEFINIR con revisión legal]**.

## 3. Enlaces a probar en ventana privada (Ctrl+Shift+N) y desde el celular con datos
Sin sesión iniciada en ninguna cuenta. Anotar hora y resultado.
- [ ] **Demo** `https://atalaya-demo.onrender.com` — abrirla justo antes de enviar (el plan gratuito se duerme; la primera carga tarda ~1 min).
  - [ ] `/health` muestra `{"status":"ok","mode":"demo","auth":false}`.
  - [ ] Sale la **intro** en la primera visita de la sesión y no vuelve al recargar.
  - [ ] Recorrido: Panel de Control → campaña «Poner en cuarentena en los 2 buzones» → motivo obligatorio → supervisor → Analítica → Historial → informe PDF → «Reiniciar demostración». Las pestañas suman el total.
  - [ ] `/docs` y `/auth/google/login` dan 404.
- [ ] **Repositorio** (enlace público): abre sin iniciar sesión en GitHub; se ve el README; no aparece `.env`.
- [ ] **Presentación** (enlace público, no archivo local): abre sin cuenta y se ven todas las láminas ([DIAPOSITIVAS.md](DIAPOSITIVAS.md)).
- [x] **Video** subido a YouTube como «no listado»: https://youtu.be/QnZj7nNyKBo (22 nov, comprobado sin sesión: carga, dura 2:18 y no muestra errores). Falta repetir la prueba desde el celular y con la hora de envío.
- [ ] **Video** (reglas generales del campo, opcional): subido como **no listado** (YouTube) o con enlace de Drive; abre sin cuenta y se oye y se ve. Si es narrado con voz sintética, que lo diga (el video ya lo dice al final).
- [ ] **Encuesta** (Google Forms): abre en ventana privada, acepta una respuesta de prueba y **no pide iniciar sesión**. Contar las respuestas reales y borrar la de prueba ([ENCUESTA_DOJO.md](ENCUESTA_DOJO.md)).
- [ ] Todos los enlaces dentro del formulario de Dojo están pegados (no escritos a mano).

## 4. Cifras y fuentes
- [ ] Abrir **cada fuente** de [EVIDENCIA_PUBLICA.md](EVIDENCIA_PUBLICA.md) que se cite y confirmar cifra, año y metodología.
- [ ] Citar cada cifra con su fuente y diciendo que viene de estudios de proveedores de seguridad. No mezclar estudios; no decir «ataques exitosos» a partir de intentos. El pitch dice «muchos ataques empiezan con un correo» (no «casi todos»: no hay fuente para eso).
- [ ] Encuesta: decir «N respuestas (M administran correo)», muestra pequeña y no representativa; sin redondear. Entrevistas: **0**.
- [ ] Precio y modelo: **hipótesis**. Sin clientes. La licencia comercial es un borrador sin revisión legal.

## 5. Qué decir sobre los límites (pitch, descripción y respuestas)
- [ ] Sin adjuntos ni reputación de enlaces.
- [ ] Solo Gmail/Google Workspace; Microsoft 365 está en la hoja de ruta, no construido.
- [ ] IA real implementada pero **sin probar con saldo** (o, si se probó, decir cuánto cuesta por correo y que se midió); en la demo la explicación es simulada y la pantalla lo dice.
- [ ] Corpus **sintético** de **62** correos escritos por el desarrollador: 27/30 detectados y 3/32 marcados de más (`python -m app.evaluate`); no es rendimiento real y parte de la mejora viene de casos escritos para las funciones nuevas.
- [ ] No detecta fraude sin señales técnicas (p. ej., «el jefe» pidiendo una transferencia sin enlaces).
- [ ] El kit se construye y se prueba en el CI y **arrancó con Docker Desktop real**; **no se probó con una organización de Google Workspace real** ni los pasos de Google Cloud.
- [ ] El permiso `gmail.modify` de Google es más amplio que lo que usa el código (solo lista, lee y etiqueta).
- [ ] Sin soporte garantizado ni acuerdo de nivel de servicio ([MARKETPLACE_FICHA.md](MARKETPLACE_FICHA.md)). **Pendiente de decidir:** si se va a ofrecer soporte o a asumir alguna responsabilidad por el producto, debe quedar escrito en un contrato revisado por una persona abogada; hoy los términos dicen «tal cual», sin garantías.
- [ ] Seguridad: prueba de intrusión propia (un fallo alto, corregido) y herramientas de análisis contra el propio equipo; no hay revisión independiente.

## 6. Preguntas a los organizadores ([PREGUNTAS_ORGANIZADORES.md](PREGUNTAS_ORGANIZADORES.md))
Según ese archivo, **siguen sin respuesta por escrito**. Preguntar en Discussions o por WhatsApp antes de enviar, o decidir sin ellas y anotarlo:
- [ ] #1 Cómo se entrega y cobra un producto en el Marketplace, y si el precio es editable (hoy «Free»). Con el modelo de kit: ¿se entrega el código o un enlace?
- [ ] #2 Demostración con datos simulados y APIs restringidas (informado verbalmente en el kickoff; falta confirmación escrita).
- [ ] #4 Qué cuenta como «demo real».
- [ ] #6 Pagos y impuestos para participantes de Panamá.
- [ ] #7 Trabajo previo (solo documentación e ideas antes del 20 nov) y cómo documentarlo.
- [ ] #8 Si el repositorio puede ser privado (el kickoff dijo que debe poder revisarse).
- [ ] #11 Licencia que se concede a Dojo sobre el proyecto (afecta a la licencia comercial).
- [ ] Créditos de API para la prueba de IA real.

## 7. Prueba de la IA real (opcional, si se logra recargar)
- [ ] Poner `ATALAYA_LLM=anthropic` en tu `.env` local y reiniciar; **no** compartir la clave ni pegarla en el chat.
- [ ] Verificar el nombre del modelo por defecto (`claude-haiku-5-5`, sin confirmar) y medir el costo por correo.
- [ ] Correr el corpus con IA real y comparar; actualizar los marcadores `[actualizar si se mide]` en [PITCH.md](PITCH.md), [DIAPOSITIVAS.md](DIAPOSITIVAS.md) y [MARKETPLACE_FICHA.md](MARKETPLACE_FICHA.md).
- [ ] Si no se prueba: dejar escrito «sin probar», como ya está.

## 8. Hora de envío
- [ ] Reloj de Windows sincronizado.
- [ ] Demo despierta justo antes de enviar.
- [ ] Relectura final del formulario completo.
- [ ] **Todo lo anterior marcado → «Submit and publish».** No pulsarlo antes de probar todos los enlaces.
- [ ] Después de enviar: abrir de nuevo la página del proyecto en Dojo en ventana privada y verificar que los enlaces publicados funcionan.

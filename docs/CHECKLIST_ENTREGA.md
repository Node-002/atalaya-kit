# Lista final antes de «Submit and publish»

> Meta propia: enviar **antes de las 10:00 p. m. (hora de Panamá) del domingo 22 nov**. Cierre oficial: 11:59 p. m. de Costa Rica (= 12:59 a. m. del lunes en Panamá), sin tiempo extra. Marcar cada casilla **solo después de probarla**. Contexto: [CRONOGRAMA_SIGUIENTE.md](CRONOGRAMA_SIGUIENTE.md), [DESPLIEGUE.md](DESPLIEGUE.md).

## 1. Enlaces a probar en ventana privada (Ctrl+Shift+N) y desde el celular con datos
Sin sesión iniciada en ninguna cuenta. Anotar hora y resultado.
- [ ] **Demo** `https://atalaya-demo.onrender.com` — abrirla justo antes de enviar (el plan gratuito se duerme; la primera carga tarda ~1 min).
  - [ ] `/health` muestra `{"status":"ok","mode":"demo","auth":false}`.
  - [ ] La página principal carga; aparece el aviso «Demostración».
  - [ ] Recorrido completo: Resumen → Correos → campaña «Poner en cuarentena en los 2 buzones» → motivo obligatorio → rol supervisor → Historial → reporte → «Reiniciar demostración».
  - [ ] `/auth/google/login` da «Not Found» y `/docs` da 404.
- [ ] **Repositorio** (enlace público): abre sin iniciar sesión en GitHub; se ve el README; no aparece `.env`.
- [ ] **Presentación** (enlace público, no archivo local): abre sin cuenta y permite ver todas las láminas ([DIAPOSITIVAS.md](DIAPOSITIVAS.md)).
- [ ] **Video** (opcional; tiene su propio campo): abre sin cuenta y se oye/ve el recorrido.
- [ ] **Encuesta** (Google Forms de la cuenta del proyecto): abre en ventana privada, acepta una respuesta de prueba y **no pide iniciar sesión**. Contar respuestas reales y borrar la de prueba ([ENCUESTA_DOJO.md](ENCUESTA_DOJO.md)).
- [ ] Todos los enlaces dentro del formulario de Dojo están escritos sin errores (copiar y pegar, no a mano).

## 2. Repositorio
- [ ] `gitleaks detect --source .` **sobre todo el historial** sin hallazgos (si hay uno, parar y avisar; **no** hacer público).
- [ ] Solo **después** de gitleaks limpio, hacer el repositorio público.
- [ ] `pytest`, `ruff check .`, `bandit -r app -x app/tests` (con `PYTHONUTF8=1`) y `pip-audit -r requirements.txt` limpios.
- [ ] **Licencia:** decidir y añadir `LICENSE` ([LICENCIA_OPCIONES.md](LICENCIA_OPCIONES.md)). Hoy no existe.
- [ ] **README:** coincide con lo que hace el código (ya se reescribió; releer con ojos de jurado), enlaces internos válidos, sección de uso de IA presente.
- [ ] Se ven las pruebas de evidencia pedidas: `CLAUDE.md`, `docs/adr/`, [USO_DE_IA.md](USO_DE_IA.md) y la descripción con un resumen (no hay campo aparte para el agentic coding).
- [ ] Primer **CI de GitHub Actions** ejecutado y en verde (nunca se ha ejecutado; se sabe al subir).
- [ ] [POLITICA_PRIVACIDAD.md](POLITICA_PRIVACIDAD.md) y [TERMINOS_DE_USO.md](TERMINOS_DE_USO.md): decidir si se publican como borrador (con la advertencia) o se dejan fuera; completar contacto.
- [ ] No hay en el repositorio `.env`, `secrets/`, `data/` ni `*.db`.

## 3. Cifras y fuentes
- [ ] Abrir **cada fuente** de [EVIDENCIA_PUBLICA.md](EVIDENCIA_PUBLICA.md) que se cite y confirmar cifra, año y metodología.
- [ ] Citar cada cifra con su fuente y diciendo que viene de estudios de proveedores de seguridad. No mezclar estudios; no decir «ataques exitosos» a partir de intentos.
- [ ] Encuesta: decir «N respuestas (M administran correo)», muestra pequeña y no representativa; sin redondear.
- [ ] Precio y modelo: marcados como **hipótesis**. Sin clientes ni entrevistas, salvo que se hayan hecho.

## 4. Qué decir sobre los límites (en pitch, descripción y respuestas)
- [ ] Sin adjuntos ni reputación de enlaces.
- [ ] Solo Gmail; Microsoft 365 no está construido.
- [ ] IA real implementada pero **sin probar con saldo**; en la demo la explicación es simulada y la pantalla lo dice.
- [ ] Corpus **sintético** de 48 correos escritos por el desarrollador: 21/24 detectados y 3/24 falsos positivos; no es rendimiento real, y la mejora respecto a 11/24 viene de casos escritos para la función nueva.
- [ ] No detecta fraude sin señales técnicas (p. ej., «el jefe» pidiendo una transferencia sin enlaces).
- [ ] Google en modo de pruebas (máx. 100 usuarios, tokens de 7 días).
- [ ] Dominios oficiales de las marcas sin verificar (decirlo o verificarlos antes: lista en `app/analyzers.py`).
- [ ] No se ha probado la imagen Docker localmente (Docker no instalado): solo vale lo que muestre el despliegue real. Si el despliegue en Render ya funciona, esto queda resuelto.

## 5. Preguntas abiertas a los organizadores ([PREGUNTAS_ORGANIZADORES.md](PREGUNTAS_ORGANIZADORES.md))
Según ese archivo, **siguen sin respuesta por escrito**. Si todavía no hay respuesta, preguntar en Discussions antes de enviar o decidir sin ella:
- [ ] #1 Cómo se entrega y cobra un producto en el Marketplace, y si el precio es editable (hoy «Free»).
- [ ] #2 Demostración con datos simulados y APIs restringidas (informado verbalmente en el kickoff; falta confirmación escrita).
- [ ] #4 Qué cuenta como «demo real».
- [ ] #6 Pagos y impuestos para participantes de Panamá («se verían después»).
- [ ] #7 Trabajo previo (solo documentación e ideas antes del 20 nov) y cómo documentarlo.
- [ ] #8 Si el repositorio puede ser privado (el kickoff dijo que es obligatorio y debe poder revisarse).
- [ ] #11 Licencia que se concede a Dojo sobre el proyecto (necesaria para decidir la licencia).
- [ ] Si se puede competir en ambos tracks; si se puede editar tras enviar (informado: sí).

## 6. Hora de envío
- [ ] Reloj de Windows sincronizado.
- [ ] Demo despierta justo antes de enviar.
- [ ] Relectura final del formulario completo.
- [ ] **Todo lo anterior marcado → «Submit and publish».** No pulsarlo antes de probar todos los enlaces.
- [ ] Después de enviar: abrir de nuevo la página del proyecto en Dojo en ventana privada y verificar que los enlaces publicados funcionan.

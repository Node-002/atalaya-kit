# Checklist del viernes 20 — de 6:00 a 10:00 (solo preparación)

> Regla: **no se escribe código de la aplicación ni se crea `app/` antes de las 10:00.** Todo lo que hagas antes se anota en `docs/ESTADO_INICIAL.md` con la hora.
> Esta noche: dormir. Alarma a las 5:45 en el teléfono. A las 9:45 suena el recordatorio programado.

## 6:00 — Estado del repositorio
- [ ] `cd C:\Hackaton` y `git status`. Si hay archivos nuevos de documentación sin guardar, revisalos y hacé un commit solo de documentos.
- [ ] Confirmá la identidad de los commits (tiene que salir tu correo `noreply`):
```bash
git log --format="%h %an <%ae>"
```
- [ ] Revisá que no haya archivos sensibles ni `.wav` en lo que se va a subir.

## 6:30 — GitHub (repositorio **privado** hasta el domingo)
- [ ] Iniciá sesión con la herramienta de GitHub (esto lo hacés vos, con tu cuenta):
```bash
gh auth login
```
- [ ] Antes de subir nada, buscá secretos en el historial:
```bash
gitleaks detect --source . --verbose
```
- [ ] Creá el repositorio privado y subí lo existente (solo documentos):
```bash
gh repo create atalaya --private --source=. --remote=origin --push
```
- [ ] En el repositorio de GitHub, **Settings**: confirmá que el nombre y el correo mostrados sean los `noreply`; activá las alertas de dependencias (Dependabot). *El escaneo de secretos de GitHub puede requerir un plan de pago en repositorios privados (verificar): por eso se usa `gitleaks` local.*
- [ ] **No lo hagas público todavía.** El formulario de Dojo acepta repositorios públicos: se cambia el domingo, después de pasar `gitleaks` y revisar el historial.
- [ ] Antes de hacerlo público, decidí qué carpetas de `docs/` quedan visibles (por ejemplo, las notas de entrevistas no deben tener datos de personas).

## 7:00 — Entorno local
- [ ] `python --version` (3.12 o superior) y `git --version`.
- [ ] Entorno virtual y herramientas (sin crear `app/`):
```bash
python -m venv .venv
```
- [ ] Instalar `gitleaks`, `bandit`, `pip-audit`, `ruff` y `pytest` (según tu sistema; verificá cada instalación en su README).
- [ ] Probá que funcionen con un comando de versión cada una.

## 7:30 — Cuentas y claves (solo configuración)
- [ ] **Claude API:** una clave **exclusiva del hackathon**, en una variable de entorno de tu usuario (nunca en el repositorio). Si tu cuenta lo permite, poné un **límite de gasto**. Anotá cuándo revocarla (el lunes).
- [ ] **Google Cloud:** proyecto en modo de pruebas, pantalla de consentimiento, usuarios de prueba (tus cuentas Gmail propias), Gmail API habilitada. Descargá las credenciales a una carpeta **fuera del repositorio**. No programes el login todavía.
- [ ] **Microsoft Entra:** solo si las entrevistas indican Microsoft como prioridad.
- [ ] **Render o Railway:** cuenta lista, sin desplegar.
- [ ] **Teléfono:** datos móviles como respaldo de internet.

## 8:30 — Material y diseño en papel
- [ ] Los **30 correos de prueba** (phishing simulado inofensivo y legítimos) en una carpeta **fuera** del repositorio por ahora.
- [ ] Lista de marcas de Panamá y Costa Rica (verificar nombres reales).
- [ ] Releé `docs/PLAN_MAESTRO.md` y `docs/MVP_ALCANCE.md`.
- [ ] Notas de las entrevistas hechas hasta ahora y decisión provisional sobre el proveedor (Gmail o Microsoft).
- [ ] Actualizá `docs/ESTADO_INICIAL.md`: todo lo hecho esta mañana, con la hora, y lo que **no** existe (código, `app/`).
- [ ] Commit solo de documentación y `git push`.

## 9:30 — Pausa
- [ ] Desayunar, agua, cerrar distracciones. Tener abiertos: terminal, editor, Dojo, `docs/PLAN_MAESTRO.md`.
- [ ] 9:45 suena el recordatorio. 10:00 arranca el hackathon: seguir "Primeras 4 horas" del plan maestro.

## No hacer antes de las 10:00
- Crear `app/` o escribir código del producto.
- Programar el login de Google.
- Subir claves, tokens o credenciales al repositorio.
- Hacer público el repositorio.
- Pulsar "Submit and publish" en Dojo.

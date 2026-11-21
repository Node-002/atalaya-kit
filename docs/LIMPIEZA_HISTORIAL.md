# Limpieza dirigida del historial (procedimiento)

**Objetivo:** retirar del historial de Git, antes de hacer público el repositorio, los datos de contacto de terceros y los datos personales que quedaron en commits antiguos, **conservando las fechas de autor y de commit, los autores, el orden y los asuntos** (la evidencia de cuándo empezó el trabajo). Solo cambian los SHA.

Este documento no contiene datos sensibles. La lista de reemplazos (que sí los contiene) vive **fuera del repositorio** y no se comitea. Contexto de la decisión: `docs/AUDITORIA_PUBLICACION.md`.

## Piezas
| Archivo | Para qué |
|---|---|
| `tools/historial/limpiar_historial.sh` | Orquesta todo: respaldo, reescritura, verificaciones (a–e). Falla si alguna no pasa. **No hace push** |
| `tools/historial/verificar_historial.py` | Verificaciones (a), (b) y (c); solo usa la biblioteca estándar |
| Archivo de reemplazos (fuera del repositorio) | Reglas `regex:PATRON==>SUSTITUTO`, una por línea, de lo específico a lo general. Los patrones de comprobación se derivan de él |

`git-filter-repo` **no** está en `requirements*.txt`: es una herramienta de un solo uso. Versión probada 2.47.0, licencia MIT (el proyecto original es MIT/GPL-2.0 dual).

## Antes de empezar
1. Integrar en `hackathon/mvp` todo el trabajo de las demás ramas y decidir qué ramas se publican. Detener las demás sesiones o worktrees que puedan escribir en el repositorio.
2. Entorno temporal con la herramienta (en una carpeta fuera del repositorio):
```powershell
python -m venv $env:TEMP\fr
& $env:TEMP\fr\Scripts\python.exe -m pip install git-filter-repo==2.47.0
$env:PATH = "$env:TEMP\fr\Scripts;$env:PATH"
```
3. Tener `gitleaks` y Git Bash (`bash`) disponibles.
4. Revisar que el archivo de reemplazos cubre todo lo que hay que retirar. Cada regla se aplica en el orden del archivo. Si se añade algo nuevo en el árbol (un documento o una prueba con datos), añadir su regla y repetir el ensayo.

## 1. Ensayo (sin tocar nada del repositorio real)
Desde la raíz del repositorio, en Git Bash:
```bash
bash tools/historial/limpiar_historial.sh /ruta/fuera/del/repo/reemplazos.txt  .  /ruta/vacia/ensayo  hackathon/mvp
```
Argumentos: archivo de reemplazos; origen (el repositorio local `.` contiene **todas** las ramas, a diferencia del remoto, que solo tiene algunas); carpeta de trabajo vacía; rama del resultado donde correr `pytest` y `ruff`.

El script hace, en este orden, y se detiene en el primer fallo:
1. **Respaldo:** espejo del original (`original.git`), lista de fechas (`original-fechas.txt`) y copia comprimida (`original.git.tar.gz`).
2. **Reescritura** en un espejo nuevo (`reescrito.git`): `git filter-repo --force --prune-empty never --prune-degenerate never --replace-text … --replace-message …`. `never` evita que se eliminen commits que queden vacíos y cambie el número o el orden. Genera `filter-repo/commit-map` (SHA antiguo → nuevo).
3. **Verificación (a):** cero coincidencias de cada patrón en todas las revisiones (`git grep -P` sobre cada commit), en mensajes y autores, en nombres de archivo y en etiquetas.
4. **Verificación (b):** fechas de autor y de commit, autores, asuntos, padres y orden idénticos; mismas etiquetas con la misma fecha y autor.
5. **Verificación (c):** para cada par de commits del `commit-map`: la misma lista de archivos y modos; los archivos que cambian solo difieren en líneas que contenían un patrón en el original y ninguno en el nuevo; se informan los conteos.
6. **Verificación (d):** `gitleaks detect --log-opts="--all"` sobre el espejo limpio.
7. **Verificación (e):** clon del resultado, entorno nuevo con `requirements-dev.txt`, `pytest` completo y `ruff check .`.

Si algo falla, no se continúa. Corregir el archivo de reemplazos y repetir el ensayo en una carpeta nueva.

## 2. Respaldo del original (guardarlo, fuera del repositorio)
El script ya deja `original.git.tar.gz` y `original-fechas.txt` en la carpeta de trabajo. Copiarlos a un lugar privado y fuera del repositorio, y anotar su huella:
```powershell
Get-FileHash original.git.tar.gz, original-fechas.txt
```
Esta copia conserva los SHA y fechas reales; es la evidencia si hace falta demostrar el orden y las fechas del trabajo. **Contiene los datos antiguos: no publicarla.** Para fuerza probatoria, además, un recibo de un tercero (por ejemplo, enviarse por correo `original-fechas.txt` y su huella). Exportar también la lista de despliegues de Render (fecha, hora y SHA), porque esos SHA dejarán de existir en el repositorio.

## 3. Push forzado (lo ejecuta una persona, a mano)
El estado remoto actual del repositorio es: rama por defecto `hackathon/mvp`, cuatro ramas de Dependabot (con cuatro solicitudes de extracción abiertas), las etiquetas `estado-inicial` e `inicio-hackathon`, sin bifurcaciones (forks) y privado. `master` y las demás ramas existen solo en local.

1. **Cerrar las solicitudes de extracción de Dependabot y borrar sus ramas** (se recrean solas después, con los SHA nuevos):
```powershell
gh pr list --repo Node-002/atalaya --state open
gh pr close 1 --repo Node-002/atalaya --delete-branch
gh pr close 2 --repo Node-002/atalaya --delete-branch
gh pr close 4 --repo Node-002/atalaya --delete-branch
gh pr close 5 --repo Node-002/atalaya --delete-branch
```
2. **Subir las ramas necesarias**, una a una, desde el espejo reescrito. No usar `--mirror`: intentaría tocar `refs/pull/*`.
```powershell
cd <carpeta-de-trabajo>\reescrito.git
git remote add origin https://github.com/Node-002/atalaya.git
git push --force origin refs/heads/hackathon/mvp:refs/heads/hackathon/mvp
```
Ramas adicionales que se quieran publicar: `git push --force origin refs/heads/<rama>:refs/heads/<rama>`. Las ramas de trabajo `claude/*`, `integracion*`, `informes`, `endurecimiento` y `master` **no hace falta subirlas**: ya están integradas o son locales. Si se sube `master` o `main`, comprobar antes que su contenido ya pasó por la limpieza (todas las ramas del espejo la pasaron).
3. **Etiquetas:** las dos existentes cambian de SHA y hay que reemplazarlas (conservan fecha y autor, lo comprueba el verificador):
```powershell
git push --force origin refs/tags/estado-inicial refs/tags/inicio-hackathon
```
4. **Ramas por defecto y protecciones:** si una regla de protección de rama bloquea el push forzado, desactivarla temporalmente en Settings → Branches y reactivarla después.
5. **No empujar nada desde clones antiguos.** Los clones y worktrees anteriores a la limpieza apuntan a SHA antiguos: un `git push` de una rama vieja reintroduce los datos. Reclonar el repositorio (o `git fetch` y `git reset --hard origin/hackathon/mvp` en un clon nuevo) antes de seguir trabajando.

## 4. Después del push
1. **CI:** abrir la pestaña Actions y comprobar que el flujo corre y pasa sobre el SHA nuevo de `hackathon/mvp` (pytest, ruff, bandit, pip-audit, gitleaks).
2. **Render:** el despliegue está ligado a la rama; comprobar que se redespliega desde el SHA nuevo y que `https://atalaya-demo.onrender.com` responde (la primera carga tarda hasta 1 min). Si Render guarda el SHA antiguo, usar «Manual deploy → Deploy latest commit».
3. **Dependabot:** se recrean las ramas y PR sobre el SHA nuevo en su próximo ciclo; revisarlos.
4. **Purga en GitHub (Soporte):** los commits antiguos siguen accesibles por su SHA y por `refs/pull/*` hasta que GitHub los elimine. Abrir una solicitud en <https://support.github.com/contact> («Remove sensitive data from a repository»), con: nombre del repositorio, SHA antiguos (columna 1 de `original-fechas.txt`; **enviar solo los SHA, no el archivo de reemplazos**), y los números de las PR. Pedir que recolecten la basura de objetos inalcanzables y que limpien las vistas en caché. Hacerlo **antes** de poner el repositorio público.
5. **Comprobar el resultado desde fuera:** clonar de cero y repetir las verificaciones sobre el clon (`git grep -P` con los patrones sobre `git rev-list --all`); abrir un SHA antiguo en la web y confirmar que ya no se ve.

## 5. Hacer público el repositorio
Solo cuando: (1) las verificaciones pasaron en el ensayo y en el clon final; (2) Soporte confirmó la purga; (3) el CI y Render están en verde sobre los SHA nuevos; (4) quedaron decididos los pendientes de `docs/AUDITORIA_PUBLICACION.md` (estrategia interna y archivos que no se publican). Si el documento de auditoría se publica, comprobar que su contenido ya pasó la limpieza o quitarlo: describe los datos que se retiraron.
```powershell
gh repo edit Node-002/atalaya --visibility public --accept-visibility-change-consequences
```
Después, abrir el repositorio en una ventana sin sesión y comprobar el README, la licencia, los enlaces y que no aparezca ningún dato retirado.

## Qué conserva GitHub como evidencia de fechas, pase lo que pase
Las fechas de autor y de commit del historial (se pueden alterar: sirven de apoyo, no de prueba); la fecha de creación del repositorio, de las solicitudes de extracción y de las etiquetas publicadas; los eventos de la cuenta y del repositorio (unos 90 días en la API de eventos); el historial de ejecuciones de Actions (registros 90 días por defecto); y el historial de despliegues de Render. Con la reescritura, los SHA que muestran esos registros dejan de existir; por eso se guarda el respaldo del original con su lista de SHA y fechas.

## Riesgos que quedan
- **Una regla incompleta deja un dato.** El ensayo comprueba solo lo que está en el archivo de reemplazos; un dato que nadie listó no se detecta. Revisar con una búsqueda amplia independiente sobre el resultado (correos fuera de `.example`, teléfonos, nombres propios).
- **Los SHA citados en cualquier lugar (README, Dojo, mensajes) dejan de ser válidos.**
- **Copias ya hechas** (clones, cachés, caché de GitHub hasta la purga) conservan el historial antiguo.
- **Los sustitutos pueden dejar frases torpes** en los documentos antiguos («de una universidad pública»), sin consecuencias.
- **Condición de carrera:** si otra sesión sube trabajo mientras se reescribe, ese trabajo no está en el espejo. Congelar el repositorio, reescribir y reclonar.

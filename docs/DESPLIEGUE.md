# Despliegue público de Atalaya (solo modo demo)

> Esto es solo para la **demo pública**. Para que una organización instale Atalaya con sus propios correos, ver el **kit autoalojado**: [INSTALACION.md](INSTALACION.md). La imagen tiene tres etapas (`base`, `kit`, `demo`); Render y `docker build .` construyen la **última** (`demo`), que sigue forzando `ATALAYA_MODE=demo`.

El enlace público usa **modo demo**: empleados simulados, sin inicio de sesión, base de
datos en memoria, sin Google ni cuentas reales. La imagen (`Dockerfile`) fuerza
`ATALAYA_MODE=demo`; no hace falta —ni conviene— poner ninguna otra variable.

## Variables a definir en la plataforma
| Variable | Valor | Para qué |
|---|---|---|
| `ATALAYA_BASE_URL` | la URL pública, ej. `https://atalaya.onrender.com` | enlaces de invitación y cabecera HSTS |
| `PORT` | la pone la plataforma sola | puerto de escucha |

Nada más. **No** pongas `ANTHROPIC_API_KEY`, claves de Google, `ATALAYA_FERNET_KEY` ni
contraseñas: la demo usa un resumen simulado y no gasta saldo.

## Render
1. Crea cuenta en render.com y conecta el repositorio de GitHub (puede seguir privado).
2. **New → Web Service**, elige el repositorio y la rama que vayas a entregar.
3. **Runtime: Docker** (detecta el `Dockerfile`). No pongas comando de inicio: ya está en la imagen.
4. Plan gratuito. En **Environment** añade `ATALAYA_BASE_URL` (puedes ponerla después de ver la URL asignada y volver a desplegar).
5. **Health Check Path:** `/health`.
6. Despliega y espera "Live".

## Railway
1. Crea cuenta en railway.app → **New Project → Deploy from GitHub repo**.
2. Railway detecta el `Dockerfile` y lo usa. No pongas comando de inicio.
3. En **Variables** añade `ATALAYA_BASE_URL` (no definas `PORT`: Railway lo inyecta).
4. En **Settings → Networking → Generate Domain** para obtener la URL pública.
5. (Opcional) En **Settings → Healthcheck Path:** `/health`.

## Comprobar que funciona
- Abre `https://TU-URL/health`: debe mostrar `{"status":"ok","mode":"demo","auth":false}`.
  Si dice `"mode":"gmail"` o `"auth":true`, **para el servicio** y revisa las variables.
- Abre `https://TU-URL/`: se ve el panel con alertas de ejemplo, sin pedir login.
- Prueba `https://TU-URL/auth/google/login`: debe dar "Not Found".
- En el plan gratuito el servicio se duerme: la primera carga puede tardar ~1 minuto.
  Ábrelo unos minutos antes de presentar.

## Ver el resultado de la imagen en el CI
Cada subida corre el trabajo **`imagen`** (después de `pruebas`). En GitHub: pestaña **Actions** → la ejecución más reciente → trabajo «Imagen Docker (construir, probar y escanear)».
1. «Construir la imagen» en verde = el `Dockerfile` compila.
2. «Tamano y capas…»: abre el **Summary** de la ejecución para ver el tamaño y `docker history`.
3. «Probar el contenedor»: cada línea `OK` / `FALLA` es una comprobación (modo demo, 404 en `/docs` y login de Google, sin cabecera `Server`, cookie `HttpOnly; SameSite=Lax`, usuario no root, `HEALTHCHECK` sano, y que `ATALAYA_MODE=gmail` sigue dando demo).
4. «Escaneo de vulnerabilidades (Trivy)»: tabla con hallazgos HIGH/CRITICAL que tengan corrección; si hay alguno, el trabajo falla. Se resuelve subiendo la imagen base o la dependencia.
Si falla, **no despliegues** esa rama en Render hasta entender el motivo. Detalle en `docs/adr/0010-ci-prueba-y-escanea-la-imagen-docker.md`.

## Probar en ventana privada
Abre una ventana privada/incógnito (Ctrl+Shift+N en Chrome/Edge) y pega la URL. Así
compruebas que funciona sin tus sesiones ni cookies, como lo verá el jurado. Prueba también
desde el celular con datos móviles.

## Qué NO hacer
- No subas `.env` ni claves al repositorio ni a la plataforma pública.
- No conectes cuentas reales de correo al despliegue público.
- No pongas `ATALAYA_MODE=gmail` ni credenciales de Google en el servicio público.
- No agregues la URL pública como URI de redirección en Google Cloud.
- El modo gmail se usa solo en tu computadora, con usuarios de prueba.

## Lista previa a «Submit and publish»
- [ ] `pytest`, `ruff check .`, `bandit -r app` y `gitleaks detect --source .` sin fallos.
- [ ] El repositorio no contiene `.env` ni claves (gitleaks limpio) antes de hacerlo público.
- [ ] `/health` muestra `mode: demo` y `auth: false`.
- [ ] La página principal carga en ventana privada y en el celular.
- [ ] Se puede aprobar/rechazar una alerta y el botón de reiniciar demo funciona.
- [ ] `/auth/google/login` da "Not Found".
- [ ] Todos los enlaces de la entrega (demo, repositorio, video, encuesta) abren sin iniciar sesión.
- [ ] La demo está despierta (ábrela justo antes de enviar).
- [ ] Solo entonces pulsa «Submit and publish».

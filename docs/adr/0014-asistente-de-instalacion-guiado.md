# ADR 0014 — Asistente de instalación guiado del kit

- **Fecha:** 2026-11-21
- **Estado:** aceptada. Probada con pruebas automáticas y un `docker` falso; **no** con Docker real ni con una organización de Google Workspace.

## Contexto
El kit autoalojado ([ADR 0012](0012-kit-autoalojado-en-lugar-de-servicio-alojado.md)) se instalaba con una guía, `docker compose` y una herramienta de verificación: copiar `.env.kit.example`, generar claves con comandos de Docker, editar a mano y acordarse de `chmod`. Es el paso donde una persona de TI no experta se atasca, y el que se muestra en el video.

## Decisión
Un asistente `tools/kit/instalar.py` (más envoltorios `instalar.sh` y `instalar.ps1`) que hace las preguntas, genera las claves y la configuración, arranca el compose, espera `/health` y ejecuta el verificador. La guía manual queda como «Opción B».

Decisiones concretas:
1. **Solo biblioteca estándar, Python ≥ 3.9, un solo archivo.** Corre fuera del contenedor, sin instalar dependencias; por eso **duplica** las validaciones (correo ASCII de `app/identity.py`, JSON de Google de `app/kit_preflight.py`) en lugar de importar `app`. Una prueba comprueba que la configuración generada pasa `kit_preflight.check`, para que no diverjan sin que nadie lo note.
2. **Los secretos nunca salen por pantalla, argumentos ni registros.** Fernet y sesión se generan con `secrets` justo antes de escribir; la copia de la clave Fernet la escribe el propio asistente (no se imprime). La clave de Anthropic solo entra por `getpass` o por la variable `ANTHROPIC_API_KEY`, nunca como bandera (los argumentos quedan en el historial y en la lista de procesos). Las llamadas a `docker` no llevan ningún secreto; el contenedor lee `.env.kit` con `env_file`.
3. **Archivos:** `.env.kit` se crea con `0600` desde el primer byte y se reemplaza de forma atómica; en Windows se aplica `icacls` (mejor esfuerzo, se avisa). No se sobrescribe una configuración existente sin confirmación explícita (`--sobrescribir` en modo no interactivo) y siempre se guarda antes una copia `*.bak-AAAAMMDD-HHMMSS`. Todas las rutas se unen con una función que impide salir de la carpeta del kit.
4. **El JSON de Google se copia a `secrets/google_client.json` con `0644` y la carpeta con `0711`.** El contenedor corre como usuario 10001 y monta el archivo en solo lectura: con `0600` del anfitrión no podría leerlo (así lo dice la guía). La carpeta con `0711` permite entrar pero no listar. El original **no puede estar dentro de un repositorio** (se busca `.git` hacia arriba) para que no se suba por error.
5. **Proxy:** con Caddy del kit o con un solo proxy propio se escribe `ATALAYA_TRUST_PROXY=1`; en local, `0`. Con más de un proxy propio se escribe `0` y se avisa, porque el kit hoy no distingue las IP reales con varios saltos. **No se escribe `ATALAYA_TRUSTED_HOPS`**: según la guía solo afecta a la demo pública, y escribirlo en el kit sugeriría una protección que no existe.
6. **Sin `data/`:** el kit guarda los datos en el volumen con nombre `atalaya-data`, no en una carpeta del anfitrión; crear `data/` sería una carpeta vacía que no se usa. Solo se crea `secrets/`.
7. **El Caddyfile se edita en sitio** (reemplaza `CAMBIAR_DOMINIO`; si ya tenía otro dominio, pide confirmación y guarda copia), porque el compose lo monta tal cual.
8. **Puertos:** se detecta si están ocupados con una conexión a `127.0.0.1` (no `bind`, que en 80/443 exigiría privilegios). Si el 8000 ya lo usa una instancia de Atalaya (`/health` con `mode: gmail`) es un aviso, no un error, para poder repetir el asistente.
9. **Sin red salvo `/health` en `127.0.0.1`;** sin `shell=True`, `eval`, descargas ni telemetría. Si falta Docker o Python, explica cómo obtenerlos; no instala nada.
10. **El verificador exige Python 3.11** (`datetime.UTC`); el asistente lo ejecuta solo si el intérprete lo cumple y avisa si no.

## Qué se probó y qué no
- **Probado:** 39 pruebas (`app/tests/test_kit_instalador.py`): validaciones, claves (Fernet válida con `cryptography`), que ningún secreto aparece en la salida ni en los argumentos de `docker`, permisos `0600` (POSIX), no sobrescribir y copia con fecha, modo no interactivo, español e inglés, y el flujo completo con un `docker` falso en el `PATH` y un `/health` simulado (también Caddy, saltos, Docker ausente o apagado, fallo de `up`, `/health` en modo demo o sin respuesta).
- **No probado:** Docker real, Google Cloud, una organización Workspace, el CI real (el paso nuevo del trabajo `kit` lo ejercitará al subir; `shellcheck` no estaba disponible en el equipo de desarrollo), `instalar.sh` en Linux/macOS, `icacls` más allá de Windows 11, ni Python 3.9 a 3.10 (solo se ejecutó con 3.12).

## Consecuencias
- Un archivo más que mantener en sincronía con `app/kit_preflight.py` y `.env.kit.example` (la prueba de coherencia lo vigila en parte).
- Reduce el riesgo de errores de configuración (`http` en producción, JSON incorrecto, `TRUST_PROXY` mal puesto) antes de arrancar.

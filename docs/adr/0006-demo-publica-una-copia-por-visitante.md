# ADR 0006 — Demo pública: una copia por visitante, con límites de uso

- **Fecha:** 2026-11-21
- **Estado:** aceptada.

## Contexto
La demo pública usaba una sola aplicación en memoria para todo el mundo. Si dos personas del jurado entraban a la vez, o una pulsaba «Reiniciar demostración» o aislaba un correo, la siguiente veía datos cambiados por otra persona. Además, la API aceptaba escrituras sin ningún límite (`/api/demo/reset`, `/api/poll`, `/api/invites`) y publicaba su documentación (`/docs`, `/openapi.json`) y la cabecera `Server`.

## Decisión
1. **Una copia de la demo por visitante.** `app/demo_sessions.py` es una aplicación ASGI que envuelve a `create_app` y reparte cada visita a su propia copia (estado simulado en memoria), identificada por la cookie `atalaya_demo_sid` (aleatoria de 24 bytes, `HttpOnly`, `SameSite=Lax`, `Secure` bajo https, 2 h). No se adopta nunca un identificador enviado por el cliente (sin fijación de sesión). Cambia solo el cableado final de `app/main.py`; el código de las rutas no se toca.
2. **Límites por dirección:** 20 visitas nuevas por minuto y 120 escrituras por minuto (`429` con `Retry-After`), ajustables con `ATALAYA_DEMO_NEW_SESSIONS_PER_MIN` y `ATALAYA_DEMO_WRITES_PER_MIN`.
3. **Memoria acotada:** máximo 200 copias vivas (`ATALAYA_DEMO_MAX_SESSIONS`), se descarta la menos usada, y caducan a las 2 h sin uso (`ATALAYA_DEMO_TTL`). `/health` y los archivos estáticos no crean copia (la plataforma consulta la salud sin cookie cada pocos segundos).
4. **Superficie mínima:** `/docs`, `/redoc` y `/openapi.json` quedan cerrados salvo `ATALAYA_DOCS=1`; la imagen arranca `uvicorn` con `--no-server-header`.
5. El modo `gmail` no cambia: una sola aplicación con login de administración.

## Consecuencias
- Cada visitante puede probar todo (aislar, reiniciar, cambiar a supervisor) sin afectar a nadie.
- Si el servicio se reinicia o la copia caduca, la persona vuelve a ver la demo inicial.
- Los límites se calculan con la dirección que ve `uvicorn` (`--proxy-headers`); detrás del proxy de Render/Railway es la de la persona. Una oficina entera con una misma dirección comparte el límite (por eso es generoso).
- Con varios procesos o instancias el estado no se compartiría; el plan gratuito usa una sola.

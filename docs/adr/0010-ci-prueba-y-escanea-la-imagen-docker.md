# ADR 0010 — El CI construye, prueba y escanea la imagen Docker

- **Fecha:** 2026-11-21
- **Estado:** aceptada.

## Contexto
El despliegue público (Render) usa la imagen del `Dockerfile`, pero en el equipo de desarrollo no hay Docker: la imagen solo se construía en Render, ya publicada. Un error en el `CMD`, en el usuario no root o en las cabeceras se habría visto en producción.

## Decisión
1. **Trabajo `imagen`** en `.github/workflows/ci.yml` (después de `pruebas`): construye `atalaya:ci`, la ejecuta y corre `.github/scripts/check-image.sh`, que verifica `/health` = `{"status":"ok","mode":"demo","auth":false}`, 404 en `/docs`, `/openapi.json` y `/auth/google/login`, ausencia de cabecera `Server`, cookie `atalaya_demo_sid` con `HttpOnly; SameSite=Lax`, proceso con uid ≠ 0, `HEALTHCHECK` en `healthy`, y que con `-e ATALAYA_MODE=gmail` la imagen sigue en modo demo. Después, **Trivy** (HIGH/CRITICAL, `ignore-unfixed`) falla el trabajo si hay hallazgos con corrección disponible. Tamaño e historial de capas van al resumen del trabajo.
2. **Acciones fijadas por SHA** de commit completo (comentario con la versión); Dependabot las actualiza, agrupadas en una PR semanal. Permisos mínimos por trabajo (`permissions: {}` global), `concurrency` con cancelación por rama, `timeout-minutes` en todo, `persist-credentials: false`, sin `pull_request_target`.
3. **Pruebas:** `pytest-timeout` (120 s, en `pyproject.toml`) para que un test colgado se corte y se vea cuál; `--cov-fail-under=90` en el CI (hoy ~95 %).
4. **Dockerfile:** `HEALTHCHECK` en forma JSON (hadolint DL3025). `USER atalaya` se queda con nombre (las pruebas lo exigen) y se anota `hadolint ignore=DL3066`; el uid fijo 10001 ya está en `useradd`.

## Consecuencias / riesgos
- Cada subida gasta unos minutos más de Actions (construcción + escaneo).
- Trivy descarga su base de vulnerabilidades: un fallo de red puede dar un rojo falso; se repite el trabajo.
- Un hallazgo nuevo en la imagen base puede poner el CI en rojo sin cambios nuestros: es lo buscado; se arregla con una imagen base nueva.
- No se probó en GitHub al escribir esto (sin Docker local): ver el paso a paso en `docs/DESPLIEGUE.md`.

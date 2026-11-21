# ADR 0004 — Despliegue público: solo modo demo, forzado en la imagen

Fecha: 2026-11-20

## Contexto
El enlace público del hackathon lo abrirá gente desconocida. El modo gmail guarda tokens
reales y exige login de administración; no debe existir en internet.

## Decisión
- La imagen Docker arranca con `ATALAYA_MODE=demo` escrito en el propio comando (`CMD`),
  así que una variable errónea en la plataforma no puede activar el modo gmail.
- La imagen copia solo `requirements.txt` y `app/`; `.dockerignore` deja fuera `.env`,
  `.git`, `.venv`, `data/`, credenciales y pruebas.
- Usuario sin privilegios; puerto desde `PORT`; `--proxy-headers` para que detrás del
  proxy HTTPS de Render/Railway se respete el esquema.
- En modo demo no hay cookies ni sesiones, y la base es `:memory:`; el único ajuste de
  código es `Strict-Transport-Security` cuando `ATALAYA_BASE_URL` empieza con `https`.
- Pruebas (`app/tests/test_deploy_demo.py`) demuestran que en demo no existen las rutas
  `/auth/google/*`, `/auth/admin/*`, `/api/me` ni `/api/security/events`.

## Consecuencias
Cada reinicio borra los datos (es lo deseado en una demo). Para usar el modo gmail hay que
correr la app localmente, fuera de la imagen pública.

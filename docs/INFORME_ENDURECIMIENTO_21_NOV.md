# Informe de endurecimiento (sábado 21 nov 2026)

> Todo se hizo en la rama local **`endurecimiento`** (sobre `hackathon/mvp`). **No se subió nada a GitHub.** Las herramientas de seguridad se usaron **solo contra tu propio equipo** (`127.0.0.1`), nunca contra Render, Google ni terceros.

## 1. Qué se cambió y por qué
| Cambio | Por qué | Verificación |
|---|---|---|
| **README veraz** | Prometía Safe Browsing, VirusTotal, adjuntos, RDAP y Tailwind, que no existen | Reescrito con lo que sí hace, lo que no hace y cómo correrlo; las instrucciones se probaron en un entorno limpio |
| **Dependencias fijadas** (`requirements.txt`, `requirements-dev.txt`) | Una versión nueva en Render podía romper la compilación justo antes de entregar | Entorno nuevo desde cero: instalación, 314 pruebas, `ruff`, `bandit`, `pip-audit` limpios |
| **CI con GitHub Actions** (`.github/workflows/ci.yml`) | Que cada subida corra pruebas, estilo, seguridad y secretos sola | YAML válido. **No se ha ejecutado**: solo se prueba al subirlo |
| **Dependabot** (`.github/dependabot.yml`) | Avisos semanales de dependencias y de Actions | YAML válido; activar también los avisos en Settings |
| **Demo con una copia por visitante** (`app/demo_sessions.py`, ADR 0006) | Dos jueces entrando a la vez se pisaban; «Reiniciar» cambiaba los datos de todos | 11 pruebas nuevas y comprobado en un servidor real con dos cookies: A aísla una campaña, B sigue viendo 3 pendientes |
| **Límites de uso en la demo** | Sin límite en reset, poll e invitaciones | 120 escrituras/min y 20 visitas nuevas/min por dirección: en un servidor real, 119 correctas y 11 con `429` |
| **Memoria acotada** | Evitar llenar el servicio gratuito | Máximo 200 copias, caducan a las 2 h; `/health` y estáticos no crean copia |
| **API sin documentación abierta** | `/docs` y `/openapi.json` listaban las 21 rutas | Ahora `404` (solo con `ATALAYA_DOCS=1`) |
| **Sin cabecera `Server`** | Revelaba el servidor | `--no-server-header` en la imagen; comprobado |
| **`HEALTHCHECK` en el Dockerfile** | Lo marcó Trivy | Pendiente de construir la imagen (Docker no está instalado) |
| **Favicon y meta descripción** | Error 404 en consola y SEO 90 | Lighthouse: SEO 100, buenas prácticas 100 |
| **Etiqueta de las tarjetas de buzón** | Lighthouse: el nombre accesible no coincidía con el texto visible | Accesibilidad 100 |
| **Cabecera sin saltos** (espacio reservado del botón de rol) | Desplazamiento de diseño en el móvil | Escritorio CLS 0,003. **Móvil sigue en 0,177** (ver pendientes) |

## 2. Resultados de las herramientas de seguridad
| Herramienta | Contra qué | Resultado |
|---|---|---|
| **OWASP ZAP 2.17** (ataque rápido: araña, pasivo y activo) | `127.0.0.1` (demo, límites altos) | 0 riesgo alto, 1 «medio» (confianza baja), 3 informativos. Ver abajo |
| **ffuf 2.3** (58 rutas sensibles: `.env`, `.git`, copias, `data/`, `app/main.py`, `static/../`, etc.) | `127.0.0.1` | Solo respondieron las rutas previstas: `/login`, `/health`, `/static/…`, `/api/invites` y `/api/audit` (propias de la demo). Todo lo demás, `404` |
| **Nmap 7.80** (puertos de interés) | `127.0.0.1` | Abiertos: 135 y 445 (Windows), 8000 (tu servidor), 8004/8005 (mis pruebas, ya cerrados). Nada inesperado |
| **Trivy 0.76** | `Dockerfile` y `requirements.txt` | 26 de 27 comprobaciones de la imagen; el fallo (falta `HEALTHCHECK`, baja) ya está corregido. **0 vulnerabilidades** en las dependencias |
| **Lighthouse** | Demo en escritorio y móvil | Escritorio: **100 / 100 / 100 / 100** (rendimiento, accesibilidad, buenas prácticas, SEO). Móvil: **92 / 100 / 100 / 100** |
| `pytest`, `ruff`, `bandit`, `pip-audit`, `gitleaks` | Todo el proyecto | Limpios (ver sección 4) |

### Alertas de ZAP, una por una
| Alerta | Dónde | Veredicto |
|---|---|---|
| *Absence of Anti-CSRF Tokens* (medio, **confianza baja**) | `form-invitar` y `form-motivo` en `/` | **Falso positivo.** Son `<form method="dialog">`: cierran un cuadro de diálogo en el navegador y no envían nada al servidor. La protección real es la cabecera obligatoria `X-Requested-With` más cookie `SameSite` (un POST sin ella recibe 403, probado) |
| *Suspicious Comments* (informativa) | `app.js` | **Falso positivo.** Coincidió con la palabra «Todo» («todo el panel») en un comentario |
| *Session Management Response Identified* (informativa) | cookie `atalaya_demo_sid` | Esperado: es la cookie de la copia de demo, aleatoria, `HttpOnly`, `SameSite=Lax` |
| *User Agent Fuzzer* (informativa) | `/` | Informativa: la página responde igual a distintos navegadores |

## 3. Por qué una copia por visitante y no solo «mensaje de aviso»
Es el punto que más afecta al jurado: la nota de «demo real» (25 %) depende de que cada persona vea una demo que funcione igual, sin que otra la altere. El diseño (ADR 0006) envuelve a `create_app` sin tocar las rutas, no adopta nunca un identificador que mande el cliente (sin fijación de sesión) y limita memoria y ritmo.

## 4. Verificación final
- Pruebas: **325 de 325** pasan (314 anteriores + 11 nuevas).
- `ruff`: sin avisos · `bandit` (sin pruebas): 0 problemas · `pip-audit`: 0 vulnerabilidades · `gitleaks`: limpio.
- Nota de rendimiento: durante esta sesión la suite tardó entre 26 s y varios minutos según la carga del equipo (escáneres en paralelo). No hay pruebas que dependan de la red.

## 5. Lo que sigue pendiente (dicho con honestidad)
1. **CLS móvil 0,177** (el umbral «bueno» es 0,1): un bloque (`main`) se desplaza al cargar los datos en pantalla de 412 px. Apliqué dos correcciones y no bastaron; falta localizar el elemento exacto. Escritorio está bien.
2. **El CI nunca se ha ejecutado.** Se sabrá al subir la rama; si falla, lo corrijo.
3. **La imagen Docker sigue sin construirse** (Docker no está instalado). El primer despliegue en Render lo probará.
4. **Semgrep y Nuclei** no se usaron: no están en winget y Semgrep funciona mejor en WSL.
5. **ZAP se ejecutó con límites altos** a propósito; con los límites reales de la demo (20 visitas/min) un escáner agresivo recibirá `429`, que es lo deseado.
6. Siguen abiertos los puntos del análisis por áreas que no se tocaron hoy: `LICENSE`, política de privacidad, dominios oficiales de las marcas sin verificar, pitch, diapositivas y video.

## 6. Cómo repetirlo
```
python -m pytest -q --cov=app
python -m ruff check .
PYTHONUTF8=1 python -m bandit -q -r app -x app/tests
python -m pip_audit -r requirements.txt
gitleaks detect --source .
trivy config Dockerfile
trivy fs --scanners vuln requirements.txt
npx lighthouse http://127.0.0.1:8000/ --preset=desktop
```

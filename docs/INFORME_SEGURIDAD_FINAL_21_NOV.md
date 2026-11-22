# Informe de la pasada final de seguridad — 21 nov 2026

Alcance: solo Atalaya, en local o en la demo propia (`atalaya-demo.onrender.com`), con peticiones sueltas y sin
escaneos agresivos. Nada contra Google, Gmail ni la infraestructura de Render. Estado probado: `hackathon/mvp`
+ los cambios de este informe.

## 1. Lista de controles

| Control | Resultado | Evidencia |
|---|---|---|
| HTTPS en todas las páginas | ✅ Cumple | `http://` responde 301 a `https://`; HSTS (`max-age=31536000`); TLS 1.0 y 1.1 rechazados, 1.2 y 1.3 aceptados; certificado válido hasta 17 feb 2027 (Google Trust Services). En el kit, TLS con Caddy es opcional: **debe exigirse** al instalar en un servidor |
| Ninguna clave en el código | ✅ Cumple | gitleaks: 0 hallazgos en 98 commits de `hackathon/mvp` y en las 7 referencias de PR; ningún `.env`, `.pem` ni `client_secret` versionado; Trivy `secret`: 0 |
| Contraseña larga y doble factor en el panel | ⚠️ Cumple por diseño, **sin documentar** | Atalaya no guarda contraseñas: el administrador entra con su cuenta de Google (su contraseña y su doble factor). La guía de instalación no menciona exigir el doble factor a los administradores |
| Copia de seguridad automática | ⚠️ Parcial | `respaldo.sh` y `restaurar.sh` existen y son consistentes, pero son **manuales**; la guía sugiere `cron` y aclara que **no se probó restaurar en un servidor real** |
| Todo actualizado | ✅ Cumple | pip-audit: 0 vulnerabilidades; Trivy (dependencias y Dockerfile): 0 críticas/altas; Dependabot sin alertas abiertas |
| Formulario protegido contra bots | ➖ No aplica | No hay formularios públicos con cuentas ni registro. La demo limita sesiones y escrituras por IP (ADR 0006/0007). Un CAPTCHA sería una función nueva |
| Límite de intentos al iniciar sesión | ✅ Cumple | 5 fallos en 15 min bloquean la dirección; el bloqueo se duplica (hasta 24 h) y persiste en la base. 29 pruebas lo cubren |
| Cada usuario solo ve sus datos | ✅ Cumple (por visitante y por rol) | En la demo, dos visitantes: la cuarentena de A no cambia nada en B; una cookie inventada no se adopta (se emite una nueva); el supervisor recibe 403 al escribir |
| Errores sin datos internos | ✅ Cumple tras un arreglo | Ver hallazgo H1 |
| Borrar lo que no usas | ✅ En su mayor parte | `/docs`, `/redoc`, `/openapi.json`, `/.env`, `/.git/config` responden 404; no se guardan cuerpos ni adjuntos; las copias de la demo expiran a las 2 h. Ver H3 |

## 2. Herramientas usadas

gitleaks, pip-audit, Trivy (fs: vulnerabilidades, secretos y configuración), bandit (como en el CI, sin `app/tests`),
ruff, Semgrep 1.186 (paquetes `python`, `owasp-top-ten`, `security-audit`, `javascript`; telemetría apagada; instalado
en un entorno aparte), curl y el módulo `ssl` de Python (HTTPS/TLS, cabeceras, rutas, errores y aislamiento).

**No se ejecutaron** en esta pasada: Nuclei y testssl.sh (no están instalados; se sustituyeron por las comprobaciones
de curl y `ssl`, que cubren menos que ellos), ZAP, Burp, ffuf y Nmap (ya se usaron antes contra el servidor local y la demo;
ver `INFORME_ENDURECIMIENTO_21_NOV.md` e `INFORME_PENTEST_DEMO_21_NOV.md`). Sin revisión independiente.

## 3. Hallazgos

| # | Gravedad | Hallazgo | Estado |
|---|---|---|---|
| H1 | Baja | Los errores 422 devolvían la estructura del validador (`type`, `loc`, `ctx`) y repetían el dato enviado | **Corregido**: `app/main.py` responde `{"detail": "Datos no validos."}`; prueba en `test_panel_security.py` |
| H2 | Baja | `verificar_instalacion.py` aceptaba cualquier esquema en la dirección del operador (`file://`, `ftp://`) | **Corregido**: solo `http://` y `https://`; prueba en `test_kit.py` |
| H3 | Informativa | `requirements.txt` instala `uvicorn[standard]` (incluye `websockets` y `watchfiles`, sin uso en producción) y `PyYAML` (solo lo usan las pruebas) | Abierto: reducir superficie y tamaño de la imagen; no se tocó para no arriesgar el despliegue a última hora |
| H4 | Baja–media (solo servidor compartido) | El JSON de la aplicación de Google queda en `0644` y su carpeta en `0711`, para que el contenedor (uid 10001) lo lea | Riesgo aceptado, documentado en el [ADR 0014](adr/0014-asistente-de-instalacion-guiado.md). Instalar en un equipo dedicado |
| H5 | Informativa | Semgrep marcó 2 usos de `urllib` con URL fija (`127.0.0.1:{puerto}/health` y Google) | Falsos positivos (ya llevan `# nosec`) |
| H6 | Informativa | HSTS sin `includeSubDomains` | Sin acción: la demo no usa subdominios |

## 4. Pendiente

- Documentar en la guía: exigir el doble factor de Google a los administradores, TLS obligatorio en servidor y programar el respaldo.
- La prueba completa de restauración de copias y la instalación con una organización de Workspace real siguen **sin verificar**.
- Tras la respuesta del soporte de GitHub: comprobar `git ls-remote origin 'refs/pull/*'` y repetir gitleaks antes de hacer público el repositorio.
- Una corrida de la suite de pruebas se colgó una vez en Windows (hilos) y pasó completa en la repetición (569 pasan, 1 se omite): intermitente, sin relación con estos cambios.

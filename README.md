# Atalaya — el agente que vigila el correo de tu organización

> Equipo **Atalaya** (una persona) · Dojo AI Hackathon, 20–22 de noviembre de 2026 · Track **Build for Business**

Atalaya revisa cada correo nuevo de los buzones de una organización pequeña (empresa, colegio, universidad), explica en español **por qué** desconfía de alguno y, **solo con la aprobación de una persona**, lo saca de la bandeja. Nunca borra ni envía correos.

**El producto es un kit autoalojado:** cada organización lo instala en su propio servidor, con su propia aplicación de Google y sus propias claves. Atalaya no recibe sus correos, tokens ni claves, y no hay servicio central que los custodie.

## El problema
El correo es una de las puertas de entrada más comunes de los ataques (phishing, enlaces engañosos, suplantación de marcas). Las organizaciones pequeñas no tienen un equipo de seguridad que revise cada mensaje, y las soluciones que existen vienen de grandes proveedores. Las cifras públicas y sus límites están en [docs/EVIDENCIA_PUBLICA.md](docs/EVIDENCIA_PUBLICA.md).

## Qué hace hoy (verificado con pruebas)
1. **Analiza cada correo nuevo con reglas calculadas por código**, no por IA:
   - autenticación del remitente (SPF, DKIM y DMARC, leídos de las cabeceras);
   - dominios parecidos a una marca, letras de otros alfabetos (homógrafos) y errores de escritura de la marca (28 marcas con dominios verificados en fuentes públicas, ver [docs/VERIFICACION_MARCAS.md](docs/VERIFICACION_MARCAS.md));
   - remitente que aparenta ser una marca pero escribe desde otro dominio;
   - «responder a» distinto del remitente, enlaces acortados, lenguaje de urgencia;
   - instrucciones ocultas dirigidas a una IA (intento de manipulación).
2. **Explica el resultado en español sencillo.** Un modelo de IA solo redacta la explicación; los hechos los calcula el código. En la demo la explicación es **simulada** y así se indica en pantalla.
3. **Etiqueta el correo y pide una decisión.** La cuarentena (quitar de la bandeja y poner la etiqueta «Sospechoso») es reversible y siempre requiere aprobación; si la decisión va en contra de Atalaya se exige un motivo escrito.
4. **Panel para la organización:** resumen por buzón, correos por grupo, historial de decisiones, informe por correo y de la organización (también en **PDF** con plantilla, para leerlo y archivarlo) y **campañas** (el mismo ataque llegando a varios buzones se aísla con una sola acción).
5. **Roles:** administración y **supervisor de solo lectura**.
6. **Invitaciones:** cada persona conecta su buzón con «Iniciar sesión con Google» y un enlace de un solo uso.

## Qué NO hace (límites honestos)
- **El permiso de Google es más amplio que lo que usa el código.** Atalaya pide `gmail.modify` (leer y etiquetar). El código solo lista y lee mensajes, y crea y modifica etiquetas: no borra ni envía, pero ese permiso de Google técnicamente permitiría más. Quien lo instala puede revisarlo en `app/providers/`.
- **No analiza adjuntos** ni consulta reputación de enlaces (Safe Browsing, VirusTotal): no está construido.
- **No detecta fraudes sin señales técnicas** (por ejemplo, un «jefe» que pide una transferencia sin enlaces).
- Solo Gmail; **Microsoft 365 no está construido**.
- La explicación con IA real (Anthropic) está implementada pero **no se ha probado con saldo real**.
- La medición de detección usa un corpus **sintético** que escribimos nosotros: 62 correos (30 intentos y 32 legítimos): 27 de 30 intentos detectados y 3 de 32 correos legítimos marcados de más; se reproduce con `python -m app.evaluate` ([docs/RESULTADOS_PRUEBAS.md](docs/RESULTADOS_PRUEBAS.md)). Parte de la mejora viene de casos escritos para las funciones nuevas: no es una medición con correos reales.
- Para el servicio alojado, Google exigiría verificar la aplicación (mientras tanto, máximo 100 usuarios de prueba). Por eso el producto se entrega como kit autoalojado con aplicación «Interna» de cada organización (ver arriba); esa vía **no está verificada con una organización real**.

## Cómo funciona
```
Gmail ──(consulta periódica, solo bandeja de entrada, últimos 7 días)──> correos nuevos
   → se enmascaran teléfonos, cuentas y cédulas → analizadores (reglas)
   → explicación (IA o simulada; el correo es dato hostil, la salida se valida) → veredicto
   → alerta en el panel + etiqueta en Gmail → decisión humana (cuarentena reversible)
```
**Privacidad:** no se guardan asunto, cuerpo ni adjuntos. Se guarda el veredicto, las señales, un identificador, el estado, el área de la organización del buzón (la asigna la administración; ADR 0011) y una lista blanca de metadatos técnicos de cabeceras (resultado de SPF/DKIM/DMARC, IP de origen, Return-Path con la parte local enmascarada, host de los enlaces neutralizado, dominio de Reply-To y un subconjunto saneado de cabeceras SMTP; máx. 2 KB por correo, sin direcciones completas; el país no se consulta; ver ADR 0010). Los tokens de Google se cifran (Fernet).

## Dos modos
| Modo | Para qué | Cuentas reales |
|---|---|---|
| `demo` (por defecto) | Demostración pública con empleados simulados, sin inicio de sesión y base de datos en memoria | No |
| `gmail` | Uso real: kit autoalojado en tu equipo o en el servidor de tu organización, con inicio de sesión de administración con Google | Sí (solo en tu propia instalación; nunca en el despliegue público) |

**El despliegue público es solo modo demo.** Ver [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md).

## Instalación para organizaciones (kit autoalojado)
Cada organización con **Google Workspace** puede instalar su propia copia de Atalaya en su infraestructura, con su propia aplicación de Google marcada como «Interna» y sus propias claves; **nosotros nunca vemos sus correos, tokens ni claves**. El kit trae `docker-compose.yml` (etapa `kit` del `Dockerfile`), un `Caddyfile` de ejemplo con HTTPS automático, `.env.kit.example`, herramientas en `tools/kit/` (verificador, respaldo, restauración) y una guía paso a paso: [docs/INSTALACION.md](docs/INSTALACION.md) (incluye una evaluación en 15 minutos en `localhost`). Razonamiento y hoja de ruta (Microsoft 365, servicio alojado más adelante): [ADR 0012](docs/adr/0012-kit-autoalojado-en-lugar-de-servicio-alojado.md). Ficha del producto: [docs/MARKETPLACE_FICHA.md](docs/MARKETPLACE_FICHA.md). **English:** [README.en.md](README.en.md), [docs/INSTALLATION.en.md](docs/INSTALLATION.en.md), [docs/MARKETPLACE_LISTING.en.md](docs/MARKETPLACE_LISTING.en.md).

**Instalación guiada:** `tools/kit/instalar.sh` (Linux/macOS) o `.\tools\kit\instalar.ps1` (Windows) hace las preguntas, genera las claves y la configuración, arranca Docker Compose y verifica al final; la guía manual sigue siendo la opción B ([docs/INSTALACION.md](docs/INSTALACION.md), [ADR 0014](docs/adr/0014-asistente-de-instalacion-guiado.md)). Probado con pruebas automáticas y un `docker` falso, y el kit arrancó con Docker Desktop real en Windows (contenedor «healthy», con claves de prueba); **no** se probó con una organización de Google Workspace real.

**Estado:** se probó en Python (arranque, comprobaciones previas y pruebas automáticas); **no se ha probado con una organización de Google Workspace real**, y el trabajo `kit` del CI ejercita Docker/Compose/Caddy; la guía de Google Cloud no se ejecutó con una organización real. La demo pública no cambia: sigue siendo solo modo demo.

## Probarlo en tu computadora (modo demo)
Requisitos: Python 3.12.
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```
Abre `http://127.0.0.1:8000`. (En Windows, `127.0.0.1` responde más rápido que `localhost`.)

Para el modo `gmail` hacen falta credenciales de Google y claves propias: ver [.env.example](.env.example) y [docs/adr/0003-buzones-invitaciones-y-administracion.md](docs/adr/0003-buzones-invitaciones-y-administracion.md). **Nunca subas el archivo `.env`.**

## Pruebas y comprobaciones de seguridad
```bash
pip install -r requirements-dev.txt
pytest                      # pruebas
ruff check .                # estilo y errores comunes
bandit -r app -x app/tests  # análisis estático de seguridad
pip-audit -r requirements.txt && pip-audit -r requirements-dev.txt   # vulnerabilidades en dependencias
gitleaks detect --source .  # secretos en el historial
```

## Cómo se usó la programación con IA
El proyecto se construyó con Claude Code (agente de programación) bajo reglas escritas en [CLAUDE.md](CLAUDE.md): cambios pequeños, pruebas antes de dar algo por terminado, seguridad no negociable y alcance congelado en [docs/MVP_ALCANCE.md](docs/MVP_ALCANCE.md). Cada decisión de arquitectura tiene su ADR en [docs/adr/](docs/adr/). Qué se pidió, qué generó la IA y qué decidió o corrigió la persona está en [docs/USO_DE_IA.md](docs/USO_DE_IA.md).

## Documentos clave
| Documento | Contenido |
|---|---|
| [docs/PLAN_MAESTRO.md](docs/PLAN_MAESTRO.md) | Plan del hackatón |
| [docs/MVP_ALCANCE.md](docs/MVP_ALCANCE.md) | Qué entra y qué no |
| [docs/REVISION_SEGURIDAD.md](docs/REVISION_SEGURIDAD.md) | Revisión de seguridad |
| [docs/ANALISIS_POR_AREAS.md](docs/ANALISIS_POR_AREAS.md) | Estado del proyecto por áreas, con puntaje |
| [docs/ETICA_LEGAL_SEGURIDAD.md](docs/ETICA_LEGAL_SEGURIDAD.md) | Ética, leyes y riesgos |
| [docs/RESULTADOS_PRUEBAS.md](docs/RESULTADOS_PRUEBAS.md) | Medición de la detección |

## Licencia
Atalaya se publica bajo la **GNU Affero General Public License v3.0 (AGPL-3.0)**; el texto completo está en [LICENSE](LICENSE). En palabras simples: puedes leer, usar y modificar el código, pero si lo ofreces a otras personas como servicio en red, debes publicar tus cambios bajo la misma licencia. Para usarlo dentro de un producto cerrado hace falta una **licencia comercial**, que se acuerda con el equipo (Atalaya) a través del perfil de GitHub de este repositorio.

© 2026 Atalaya. Los avisos de software de terceros irán en [NOTICE](NOTICE) cuando se integren los iconos y las fuentes.

## Aviso
Atalaya es una herramienta de apoyo, no una garantía de seguridad. La decisión final es siempre de una persona.

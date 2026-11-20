# Plan maestro — Atalaya (en solitario)

> Fecha: 19 nov 2026. Hora de Panamá. Inicio: viernes 20, 10:00 a. m. Cierre: dom 22, 11:59 p. m. de Costa Rica (12:59 a. m. del lunes en Panamá), sin prórroga. Meta propia: entregar antes de las 10:00 p. m. del domingo.

## 1. Qué voy a hacer
**Una frase:** un agente web que vigila el correo de pequeñas organizaciones, analiza cada mensaje nuevo, explica los riesgos en español sencillo, actúa en lo seguro y pide aprobación humana en lo crítico.

**Track:** Build for Business (problema 30 %, demo real 25 %, negocio 25 %, UX 20 %).

**Entregables obligatorios:** repositorio con README (qué hace y para quién, cómo correrlo, cómo usé agentic coding) + pitch deck con enlace. Opcional: video.

**MVP (recorrido único):** correo → análisis por reglas → explicación con IA → decisión por riesgo → etiqueta/acción → alerta en panel → aprobación humana → auditoría. Detalle en `docs/MVP_ALCANCE.md`.

**Modo demo público:** bandeja simulada, sin conectar cuentas reales. Es lo que prueban los jueces y los visitantes del Marketplace.

**No entra:** Microsoft completo (salvo que sobre tiempo), análisis de correo saliente, borrar o enviar correos, multiorganización, facturación.

## 2. Cómo lo voy a hacer
### Arquitectura
```
Panel web (HTML/JS)  <->  API FastAPI
                              |
        +---------------------+------------------------+
        |                     |                        |
  MailProvider          Analizadores              Almacén SQLite
  (Gmail | Demo |      (autenticación,           (veredictos, señales,
   Microsoft*)          dominios, enlaces,         estado de cobertura,
        |               urgencia)                  auditoría; SIN cuerpos)
        |                     |
        +----> Motor de decisión <---- Explicación con IA (JSON validado)
                    |
              Acciones: etiqueta / cuarentena (con aprobación)
```
`*` Microsoft solo si Gmail ya funciona de punta a punta (corte: sábado 12:00).

### Contrato de API (definir en el ADR 0001)
- `GET /api/alerts` · `GET /api/alerts/{id}`
- `POST /api/alerts/{id}/approve` · `/reject` · `/legit`
- `GET /api/coverage` (estado de cada cuenta conectada)
- `POST /api/demo/reset` (modo demo)
- `GET /auth/google/login` · `GET /auth/google/callback` · `POST /auth/disconnect`

**Alerta:** `id`, `message_ref` (hash, no el contenido), `received_at`, `sender_domain`, `risk` (`low|medium|high`), `signals[]`, `explanation`, `status` (`new|labeled|pending_approval|quarantined|dismissed`), `actions[]`.
**Regla de privacidad:** no se guardan cuerpos ni adjuntos.

### Stack recomendado y por qué
| Capa | Elección | Motivo |
|---|---|---|
| Lenguaje | Python 3.12 | Lo dominás |
| API | FastAPI + pydantic v2 | Rápido de montar; pydantic valida entradas y la salida de la IA |
| Datos | SQLite | Sin servidor ni configuración |
| Correo | `google-auth-oauthlib` + `google-api-python-client` | Cliente oficial de Gmail |
| Cifrado | `cryptography` (Fernet) | Cifrar tokens en reposo |
| IA | SDK `anthropic` | Explicación estructurada |
| Pruebas | `pytest` | Métricas sobre los 30 correos |
| Calidad | `ruff`, `bandit`, `pip-audit`, `gitleaks` | Revisión local y gratuita |
| Interfaz | HTML + JS simple + CSS ligero | Cero complejidad de build |
| Despliegue | Render o Railway (Dockerfile) | Despliegue desde GitHub |

**Evitar:** React/Node, ORMs pesados, colas externas, microservicios. Un bucle asíncrono de consulta basta.

*Nota:* los servicios gratuitos de alojamiento suelen "dormirse" tras un tiempo sin uso (verificar). Para la demo, probar el enlace justo antes de cada revisión o usar un plan mínimo de pago.

## 3. Seguridad (decisiones desde el primer commit)
- **Secretos:** `.env` fuera de git, `.env.example` sin valores; `gitleaks` antes de cada commit.
- **Tokens OAuth:** cifrados con Fernet; la clave en variable de entorno; nunca en logs. Permisos mínimos (confirmar en la documentación de Gmail cuál es el mínimo que permite leer y etiquetar). `state` en OAuth y PKCE.
- **Sesión del panel:** cookie `HttpOnly` y `SameSite`; protección contra CSRF en los botones de aprobar y rechazar; contraseña de administrador por variable de entorno en la versión conectada.
- **Salida del navegador:** escapar todo el contenido de correos; no renderizar HTML de correos.
- **IA y prompt injection:** el correo es **dato hostil**. Delimitarlo, no darle herramientas a la IA, exigir salida JSON validada con pydantic y descartar lo que no cumpla el esquema. Enmascarar teléfonos, cuentas y cédulas antes de enviarlo.
- **Hechos por código:** SPF/DKIM/DMARC, dominios parecidos y enlaces los calcula el programa; la IA solo redacta.
- **Reversibilidad:** nunca borrar correos; cuarentena = quitar de la bandeja + etiqueta, y solo con aprobación humana.
- **Auditoría:** registrar quién aprobó qué y cuándo.
- **Modo demo:** sin OAuth ni cuentas reales.

## 4. Costos y "tokens"
### Uso de Claude durante el desarrollo
*(No conozco los límites de tu plan: revisalos. No uses varias cuentas para esquivar límites; no es una práctica segura ni confiable.)*
- **Un modelo según la tarea:** el más potente para diseño de arquitectura y revisión de seguridad; uno intermedio para implementar; el más ligero para tareas mecánicas (renombrar, formatear, generar datos de prueba).
- **Sesiones cortas, una tarea por sesión.** Limpiá o compactá el contexto entre tareas.
- **Modo de planificación primero:** acordar el plan antes de generar código evita rehacer.
- **Pedir lo mínimo:** "mostrame solo el diff", "no releas el archivo completo". Referenciar archivos por ruta en vez de pegarlos.
- **Menos herramientas conectadas:** cada servidor o plugin activo agrega descripciones al contexto. Dejá activos solo los necesarios.
- **Evitar imágenes repetidas** (capturas largas consumen mucho); usar texto cuando se pueda.
- **Tareas largas y ruidosas** (búsquedas, escaneos) en un subagente o en una sesión aparte.
- **Convertir PDF a Markdown una vez** (por ejemplo con MarkItDown) en lugar de adjuntarlos varias veces.

### Uso de la API en el producto
- **Reglas primero.** La IA solo se llama para riesgo medio o alto.
- **Modelo ligero** para las explicaciones; uno más potente solo para casos ambiguos.
- **Recortar el correo** antes de enviarlo (asunto, remitente, partes relevantes) y limitar `max_tokens`.
- **Guardar la explicación** y no repetir la llamada para el mismo correo.
- **Presupuesto:** una clave de API exclusiva del hackathon con límite de gasto (si tu cuenta lo permite); medir los tokens por correo en las pruebas; revocar la clave al terminar.
- **Verificar precios y nombres de modelos** en la documentación oficial antes de fijar el costo por buzón del pitch (la skill `claude-api` ayuda).

## 5. Skills y plugins para este hackathon
| Herramienta | Para qué | Cuándo |
|---|---|---|
| **Security Guidance** (instalado) | Revisa código generado mientras trabajás | Todo el hackathon |
| **claude-security** (instalado) | Auditoría profunda | Domingo temprano, una vez |
| **`/security-review`** (integrado) | Revisión de cambios pendientes | Antes de cada hito importante |
| **claude-api** (skill) | Uso correcto del SDK, modelos, estructura de salida, costos | Cuando implementés la explicación con IA |
| **Plugin Producto** (`write-spec`) | Redactar `PRD.md` | Viernes 10:00 |
| **Plugin Ingeniería** (`architecture`, `testing-strategy`, `documentation`, `code-review`) | ADR, pruebas, README | A lo largo del hackathon |
| **Plugin Diseño** (`ux-copy`, `accessibility-review`) | Mensajes en español y accesibilidad (UX 20 %) | Sábado |
| **pptx o Canva** | Pitch deck | Domingo |
| **MarkItDown** (opcional) | Convertir PDF de leyes a Markdown | Solo si lo necesitás |
| **CLAUDE.md** (adaptar las 4 reglas tipo Karpathy) | Reglas de trabajo y evidencia exigida por Dojo | Viernes 10:00 |

**No instalar durante el hackathon:** Superpowers (flujo pesado), Claude Octopus, Firecrawl, Perplexity. Menos riesgo y menos consumo.

## 6. Primeras 4 horas (viernes 10:00–14:00)
1. **10:00–10:45** — Rama de trabajo, estructura `app/`, `PRD.md`, `CLAUDE.md`, `docs/adr/0001-interfaz-proveedor-de-correo.md`, `.env.example`, primer commit "inicio del hackathon".
2. **10:45–11:30** — FastAPI mínima con `/health`, modelos pydantic del contrato y `DemoProvider` con 3 correos de ejemplo. Primer recorrido completo con datos simulados (panel pobre, pero de punta a punta).
3. **11:30–13:30** — Login de Google y lectura de 5 correos de una cuenta de prueba. **Hito: 5 correos listados.**
4. **13:30–14:00** — Punto de control: si el login falla, Plan B (entrada manual); si funciona, seguir.

Así, desde el primer día existe un recorrido que se puede demostrar, aunque el login real todavía no esté.

## 7. Riesgos y respuestas
| Riesgo | Respuesta |
|---|---|
| OAuth se complica | Plan B: entrada manual y modo demo |
| Se agotan los tokens de Claude | Sesiones cortas, modelo ligero para lo mecánico, revisar límites antes de empezar |
| Falla el despliegue | Desplegar el sábado, no el domingo; Dockerfile desde el viernes |
| Falta documentación | ADR y README se escriben mientras se construye, no al final |
| Cansancio | Dormir 6 horas mínimo; comer; cortar a medianoche |

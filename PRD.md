# PRD — Atalaya

> Estado: v0.1, viernes 20 nov 2026 (inicio del hackathon). Documento vivo. Detalle de alcance: `docs/MVP_ALCANCE.md`. Negocio y problema: `docs/NEGOCIO_Y_PROBLEMA.md`.

## 1. Problema
Las organizaciones pequeñas (negocios, colegios, ONG, estudios contables) de Panamá y Costa Rica reciben phishing y mensajes fraudulentos en el correo, pero no tienen un equipo de seguridad que revise cada mensaje. Quien administra el correo suele ser una sola persona, sin tiempo ni formación para analizar cabeceras y enlaces.

**Hipótesis a validar con entrevistas (no son hechos):** el dolor se repite, hoy se resuelve "con cuidado" o con el filtro del proveedor, y existe disposición a pagar una suscripción baja. Los resultados se anotan en `docs/NEGOCIO_Y_PROBLEMA.md`.

## 2. Usuarios
- **Administrador (principal):** persona que gestiona el correo de la organización. Necesita ver qué es sospechoso, entender por qué y decidir con un clic.
- **Empleado (indirecto):** recibe el correo; se beneficia de que lo peligroso llegue marcado o fuera de la bandeja.
- **Jurado y visitantes del Marketplace:** prueban el **modo demo** sin conectar cuentas.

## 3. Propuesta
Un agente web que vigila el correo, analiza cada mensaje nuevo, explica el riesgo en español sencillo, actúa solo en lo seguro (etiquetar) y pide **aprobación humana** para lo crítico (cuarentena). Todo reversible y auditado.

## 4. Historias de usuario
1. Como administrador, quiero conectar el correo de mi organización con permisos mínimos y poder desconectarlo cuando quiera.
2. Como administrador, quiero que cada correo nuevo se analice y se clasifique en bajo, medio o alto riesgo.
3. Como administrador, quiero leer **por qué** un correo es sospechoso, en lenguaje sencillo.
4. Como administrador, quiero aprobar o rechazar la cuarentena, o marcar el correo como legítimo.
5. Como administrador, quiero saber si Atalaya dejó de vigilar una cuenta (acceso revocado).
6. Como administrador, quiero un registro de quién aprobó qué y cuándo.
7. Como visitante, quiero probar todo el flujo con una bandeja simulada sin conectar mi correo.

## 5. Requisitos funcionales
| # | Requisito | Prioridad |
|---|---|---|
| F1 | Interfaz `MailProvider` común con implementaciones Demo y Gmail (Microsoft solo si sobra tiempo) | Obligatorio |
| F2 | Análisis por reglas: SPF/DKIM/DMARC, dominio parecido a marcas CR/PA, remitente vs. respuesta, acortadores, urgencia | Obligatorio |
| F3 | Explicación con IA con salida JSON validada; el correo es dato hostil; datos personales enmascarados | Obligatorio |
| F4 | Motor de decisión: bajo = nada; medio = etiqueta "Revisar"; alto = etiqueta "Sospechoso" + aprobación para cuarentena | Obligatorio |
| F5 | Acciones reversibles en Gmail (etiqueta; cuarentena = quitar de bandeja + etiqueta). Nunca borrar | Obligatorio |
| F6 | Panel de alertas con señales, explicación y botones Aprobar / Rechazar / Es legítimo | Obligatorio |
| F7 | Estado de cobertura (conectada / sin cobertura por token revocado) | Obligatorio (básico) |
| F8 | Registro de auditoría | Obligatorio |
| F9 | Modo demo público con bandeja simulada (phishing, legítimo, inyección de prompt) | Obligatorio |

## 6. Fuera de alcance
Conector Microsoft completo, correo saliente/DLP, borrar o enviar correos, multiorganización, facturación, verificación de Google para uso público, OCR.

## 7. Requisitos no funcionales
- **Seguridad y privacidad:** ver `CLAUDE.md`. No se guardan cuerpos ni adjuntos; tokens cifrados; el despliegue público solo funciona en modo demo.
- **Rendimiento:** consulta cada minuto; un correo analizado en pocos segundos.
- **Costo:** reglas primero; IA solo para riesgo medio/alto; explicación guardada, sin llamadas repetidas.
- **Accesibilidad y UX:** riesgo con color **y** texto, teclado, español sencillo, un camino principal.

## 8. Contrato de API (borrador; se fija en ADR 0001)
`GET /api/alerts` · `GET /api/alerts/{id}` · `POST /api/alerts/{id}/approve|reject|legit` · `GET /api/coverage` · `POST /api/demo/reset` · `GET /auth/google/login` · `GET /auth/google/callback` · `POST /auth/disconnect`

**Alerta:** `id`, `message_ref` (hash), `received_at`, `sender_domain`, `risk` (`low|medium|high`), `signals[]`, `explanation`, `status` (`new|labeled|pending_approval|quarantined|dismissed`), `actions[]`.

## 9. Métricas de éxito
- Sobre ~30 correos de prueba: aciertos y falsos positivos medidos con un script.
- Un ajeno completa el recorrido en modo demo en menos de 2 minutos sin ayuda.
- Costo medido de IA por correo analizado (insumo para el precio).

## 10. Definición de terminado
Ver `docs/MVP_ALCANCE.md` (7 puntos): phishing detectado, legítimo sin alarma, inyección de prompt resistida, cuarentena aprobada, cobertura revocada visible, métricas sobre ~30 correos, desplegado con enlace público.

## 11. Riesgos
| Riesgo | Respuesta |
|---|---|
| OAuth de Google se complica | Plan B: entrada manual y modo demo (corte vie 14:00) |
| Gmail restringido para uso público | Público = solo demo; conexión real solo con usuarios de prueba |
| Falsos positivos | Medir; aprobación humana en lo crítico; botón "Es legítimo" |
| Prompt injection | Dato hostil, salida validada, sin herramientas para la IA, prueba dedicada |
| Tiempo | Recorte ordenado en `docs/CRONOGRAMA.md` |

## 12. Preguntas abiertas
- Proveedor prioritario (Gmail vs. Microsoft 365): lo deciden las entrevistas.
- Flujo de cobro y entrega en el Marketplace de Dojo: pendiente de respuesta por escrito.
- Precio: hipótesis a definir el sábado.

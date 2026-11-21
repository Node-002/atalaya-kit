# Uso de herramientas de IA

La entrega del hackathon exige explicar **cómo se usaron las herramientas de AI coding** y **qué se construyó**.
Se actualiza durante el hackathon, con ejemplos reales.

## Herramientas
| Herramienta | Para qué se usa |
|---|---|
| Claude (Claude Code, en el escritorio) | Planificación, análisis, redacción, generación y revisión de código |
| Plugins de seguridad (Security Guidance, claude-security) | Revisión de vulnerabilidades en el código generado |
| privacy-legal, market-researcher | Evaluación de impacto de privacidad y análisis de competencia |

## Fase previa (hasta el 19 de nov de 2026)
- Exploración de ideas, análisis comparativo y elección del proyecto.
- Redacción de documentación, notas de ética/legalidad y guion de pitch.
- Un borrador de diapositivas de una idea descartada.
- **No se generó código del producto.**

## Fase de hackathon (20–22 nov)
Completar durante el trabajo. Para cada pieza importante, anotar:

| Fecha/hora | Qué se pidió a la IA | Qué generó | Qué corregí o decidí yo |
|---|---|---|---|
| 20 nov, mañana | Redactar `CLAUDE.md`, `PRD.md` y ADR 0001 a partir de los documentos de planificación | Borradores de los tres archivos y `.env.example` | Revisé el alcance; detecté y corregí que `.gitignore` bloqueaba `.env.example`; verifiqué commits con correo noreply |
| 20 nov, mañana | Esqueleto de `app/`: modelos, `MailProvider`, `DemoProvider`, reglas, decisión, API y pruebas | Código de ~10 archivos y 11 pruebas | Revisé contra el contrato; `ruff` y `bandit` limpios; decidí que Gmail se prueba solo localmente y el público es solo demo |
| 20 nov, tarde | Reestructurar el panel para una organización con varios buzones: pestañas, resumen por buzón, campañas, rol de supervisor de solo lectura y pulido visual | Código y pruebas (`campaigns.py`, rol en `admin.py`, `org-report`, panel en `app/static/`, ~25 pruebas nuevas) y ADR 0004 | Decidí yo el modelo (una organización con varios buzones), autoricé campañas y supervisor fuera del alcance, y las reglas: la acción de campaña usa la misma regla de motivo que la individual, el supervisor se bloquea en el servidor, nunca se borra ni envía. Revisé las capturas del panel |
| 21 nov, noche y 22 nov | Redactar los documentos de entrega: guion del pitch (`PITCH.md`), esquema de diapositivas, resumen de negocio, borradores de política de privacidad y términos, opciones de licencia y lista final de entrega; revisar `invite.html` contra el código | Borradores de esos documentos (solo texto, sin cambios de código), con cifras tomadas del repositorio y de `docs/EVIDENCIA_PUBLICA.md` y un anexo con diferencias entre `invite.html` y el código | Pendiente de la persona autora: revisar cada borrador, abrir y confirmar las fuentes de las cifras, elegir licencia y precio, definir el contacto y decidir si los textos legales se publican como borrador. Los textos legales **no** los revisó una persona abogada |

## Qué hizo la persona (no la IA)
Anotar decisiones de diseño, pruebas, correcciones de seguridad y validaciones que se hicieron manualmente.

## Reglas personales
- Revisar todo el código generado antes de confirmarlo.
- Nunca pegar claves, tokens ni correos reales en el chat de IA.
- Registrar los prompts más relevantes (sin datos sensibles).

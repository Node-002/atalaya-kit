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

## Qué hizo la persona (no la IA)
Anotar decisiones de diseño, pruebas, correcciones de seguridad y validaciones que se hicieron manualmente.

## Reglas personales
- Revisar todo el código generado antes de confirmarlo.
- Nunca pegar claves, tokens ni correos reales en el chat de IA.
- Registrar los prompts más relevantes (sin datos sensibles).

# Resultados de detección — corpus de 30 correos (20 nov 2026)

> Reproducir: `python -m app.evaluate` (tabla) o `python -m app.evaluate --json`. Corpus en `app/tests/fixtures/corpus.json`.
> **Advertencia metodológica:** los 30 correos son **sintéticos** y los escribió el propio desarrollador, que conoce las reglas. No son una muestra representativa del correo real. Se incluyeron a propósito casos difíciles para no inflar los números. Las cifras son **orientativas**, no una medición de rendimiento en producción.

## Composición
14 phishing (incluye 3 difíciles sin señales técnicas) y 16 legítimos (incluye 4 que parecen sospechosos). Un correo cuenta como "marcado" si el riesgo es **medio o alto**.

## Resultados
| Medida | Primera corrida | Tras corregir un defecto |
|---|---|---|
| Phishing detectado | 11/14 (79 %) | 11/14 (79 %) |
| Falsos positivos | 4/16 (25 %) | **3/16 (19 %)** |
| Precisión de "riesgo alto" | 88 % (8 marcados) | 88 % (8 marcados) |

**Defecto encontrado por el corpus (L06):** la regla de dominio parecido marcaba cualquier dominio que *contuviera* "bac" (por ejemplo `backups-empresa`). Ahora las marcas cortas solo cuentan como palabra completa. Además, los subdominios oficiales (`mail.bancogeneral.com`) ya no se marcan como falsos. Ambos tienen pruebas.

## Lo que NO se detecta (limitaciones reconocidas)
| Caso | Qué es | Por qué falla |
|---|---|---|
| P06 | Fraude de factura (cambio de cuenta bancaria), solo respuesta a otro dominio | Una sola señal técnica débil (20 pts) |
| P08 | Fraude del jefe: "haz una transferencia hoy, no se lo digas a nadie" | Sin señales técnicas; es ingeniería social pura |
| P13 | Enlace a un sitio desconocido, sin urgencia y con autenticación correcta | Faltan reputación de enlaces y análisis del texto |

Son casos de **significado**, no de cabeceras. Es donde la explicación con IA y la reputación de enlaces (Safe Browsing) deberían ayudar; **todavía no están integradas ni medidas.**

## Falsos positivos que quedan
| Caso | Qué es | Comentario |
|---|---|---|
| L03 | Boletín con enlace acortado y "ahora mismo" | Marketing legítimo con el mismo estilo que el phishing |
| L08 | Taller sin DKIM con plazo de 24 horas | Límite exacto (30 pts); empresas pequeñas suelen no tener DKIM |
| L14 | Persona real que escribe "ignora las instrucciones anteriores del formulario" | La regla de inyección de prompt es muy estricta (60 pts) y no distingue contexto |

Para estos casos, la **aprobación humana** (nunca se aísla sin tu decisión) y el botón "Es legítimo" son la salvaguarda.

## Qué no se debe afirmar en el pitch
- Que Atalaya "detecta el 79 %" del phishing real: solo se midió sobre este corpus sintético.
- Que no hay falsos positivos.
- Que la IA ya mejora estos números: aún no se probó.

## Siguiente
1. Medir el efecto de la explicación con IA sobre P06, P08 y P13 (y sobre L03, L08, L14) cuando esté integrada.
2. Ampliar el corpus con correos de las pruebas reales de Gmail y, si es posible, correos de phishing públicos anonimizados.
3. No ajustar las reglas solo para mejorar estos números (riesgo de sobreajuste al corpus propio).

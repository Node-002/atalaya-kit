# Reglas oficiales y tracks — Dojo AI Hackathon

## Reglas (resumen de lo publicado por Dojo)
| Tema | Regla | Qué significa para vos |
|---|---|---|
| Fechas | Del 20 al 22 nov 2026. Inicia viernes 20, 9:00 a. m. (Costa Rica, UTC−6) | En Panamá (UTC−5) empieza a las **10:00 a. m.** |
| **Cierre de entrega** | **Domingo 22, 11:59 p. m. hora de Costa Rica** | En Panamá son las **12:59 a. m. del lunes 23**. Entregá antes de las **10:00 p. m. (hora de Panamá)** del domingo. |
| Modalidad | En línea desde LATAM; el encuentro del viernes es opcional e independiente | Podés competir 100 % virtual |
| Equipos | Solo o hasta 4 personas; cada integrante se inscribe y se une al equipo en Dojo | Si se suma alguien, debe inscribirse él también |
| AI coding | Hay que usar herramientas de AI coding y **explicar en la entrega cómo las usaste y qué construiste** | Llevá un registro de cómo usás la IA (ver abajo) |
| Proyectos existentes | Se puede continuar uno previo, pero hay que **documentar su estado al empezar** y distinguir el avance del 20–22 | Se evalúa el progreso durante el hackathon |
| Entrega | En Dojo, completando todos los campos; los enlaces deben permitir revisar lo construido; la publicación es automática | Enlaces públicos y funcionando |

## Consecuencias prácticas
- **No escribas el producto antes del 20.** La preparación (cuentas, claves, datos de prueba, documentos) está bien.
  Si probás OAuth antes, anotá en `docs/ESTADO_INICIAL.md` qué hiciste y qué no, con fecha.
- **`git init` el viernes 20** y hacé commits frecuentes. El historial prueba el avance durante el hackathon.
- **Registro del uso de IA:** guardá un archivo `docs/USO_DE_IA.md` con herramientas usadas, para qué y ejemplos de prompts.
- **Entrega:** repositorio público (sin claves), demo en línea, video de respaldo y descripción. Probá los enlaces en una ventana privada.
- **Hora:** poné una alarma a las 8:00 p. m. (Panamá) del domingo y entregá antes de las 10:00 p. m.

## Tracks
| Track | Descripción oficial (resumen) | Premio mostrado |
|---|---|---|
| **01 · AI Apps & Tools** | Herramienta o integración funcional con AI coding. Demostrar quién la necesita y qué mejora al usarla. | $500 |
| **02 · AI Operators** | Agentes de IA que llevan un proceso de negocio de principio a fin. Demostrar qué acciones ejecutan, qué resultado entregan y dónde interviene una persona. | $500 |

(El monto se tomó de una captura; confirmá en Dojo si hay otros premios, cómo se elige el track y si se puede participar en ambos.)

## Cuál elegir: Track 02 — AI Operators
Atalaya encaja en los dos, pero **mejor en el 02**, porque ya es un proceso de principio a fin con una persona en el circuito:

| Lo que pide el track | Cómo lo cumple tu proyecto |
|---|---|
| Un proceso de negocio de principio a fin | Detectar correo nuevo → analizar → decidir → actuar → informar |
| Qué acciones ejecuta | Etiqueta el correo en Gmail, genera la alerta, actualiza el estado de cobertura, resume el día |
| Qué resultado entrega | Bandeja protegida + panel de alertas + informe de cobertura |
| Dónde interviene una persona | El responsable aprueba las acciones de alto impacto (cuarentena), revisa casos dudosos y marca falsos positivos |

### Diseño del agente ("Operator")
```
1. Detecta     correo nuevo (cada minuto)
2. Analiza     reglas + reputación + IA (el correo = dato hostil)
3. Decide      según el riesgo:
                 bajo   → no hace nada
                 medio  → etiqueta "Revisar" + avisa
                 alto   → etiqueta "Sospechoso" + alerta urgente y PIDE APROBACIÓN para cuarentena
4. Actúa       etiqueta, alerta, registra
5. Persona     aprueba / rechaza / marca "es legítimo"
6. Informa     panel de cobertura y resumen diario
```
**Autonomía graduada:** el agente actúa solo en lo reversible y de bajo impacto (etiquetar, avisar); lo
irreversible (mover, borrar) requiere una persona. Es buena práctica de seguridad y responde justo a "dónde
interviene una persona".

### Si preferís el Track 01
Presentarlo como "integración de seguridad para Gmail": énfasis en quién la necesita (pymes, colegios) y qué
mejora (menos riesgo, explicaciones claras, privacidad). La base técnica es la misma.

## Cómo se evaluará (suposición a verificar)
Las reglas no publican criterios. Es razonable asumir: problema real, demo funcional, uso de AI coding,
claridad de la entrega y progreso durante el hackathon. Preguntá en Dojo si hay una rúbrica.

## Preguntas para el organizador
- [ ] ¿Se puede entrar a ambos tracks o hay que elegir uno?
- [ ] ¿Cuántos premios hay por track y cómo se paga a participantes fuera de Costa Rica?
- [ ] ¿Hay criterios de evaluación publicados?
- [ ] ¿Hay requisitos de formato para la entrega (video, repositorio, demo en línea)?
- [ ] ¿Se permite usar APIs de pago o cuentas de terceros para la demo?

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

## Actualización (17 nov): los tracks aparecen con otros nombres en el formulario
El formulario del proyecto en Dojo ahora ofrece dos opciones: **Build for Builders** y **Build for Business**. Antes del cambio, el proyecto estaba en **AI Operators**, y el formulario lo muestra ahora como **Build for Business**. Es probable (sin confirmar) que Dojo haya renombrado o migrado los tracks.
- Pendiente: leer la pestaña **Tracks** de la página del hackathon para confirmar la descripción actual de cada uno y su premio.
- Si "Build for Business" corresponde al antiguo AI Operators (agente que lleva un proceso de negocio de principio a fin, mostrando dónde interviene una persona), **se mantiene la elección**.
- Preguntar a los organizadores si el cambio de nombre afecta los criterios de evaluación.

## Track confirmado (17 nov): Build for Business — criterios oficiales
Descripción publicada por Dojo: soluciones para problemas reales; elegir un dolor conocido (proceso lento, tarea repetitiva, cliente mal atendido) y resolverlo con IA en un fin de semana. Los mejores proyectos pueden explorar colaboración con Dojo Coding. Premio mostrado: $500.

| Criterio | Peso |
|---|:--:|
| Claridad y tamaño del problema | 30 % |
| Que la solución funcione (demo real) | 25 % |
| Potencial de negocio y monetización | 25 % |
| Experiencia de usuario | 20 % |

**Esto reemplaza la suposición anterior** de que los criterios no estaban publicados y de que el enfoque era el de "AI Operators" (agente con persona en el circuito). Esa característica sigue siendo valiosa, pero ya no es un criterio en sí.

Implicaciones:
- 55 % depende de **demostrar el problema y el negocio**, no de la técnica. Hacen falta entrevistas reales y un modelo de negocio claro (ver `docs/NEGOCIO_Y_PROBLEMA.md`).
- La demo debe **funcionar de verdad** (25 %): modo demo estable y un recorrido completo sin fallos.
- La experiencia de usuario pesa 20 %: panel claro, mensajes en español sencillo, accesibilidad.

## Descripción oficial del hackathon (compartida el 17 nov): modelo de Marketplace
- Lema: "Llegá con una idea. Salí con un producto que se vende." Tres días para construir algo real con herramientas de AI coding y **publicarlo en Dojo Marketplace**, donde builders y empresas compran.
- **El creador se queda con el 85 % de cada venta** ("para siempre", según la descripción).
- **$1 000 en premios:** dos tracks de $500 cada uno. El jurado evalúa el **23 de noviembre**.
- **Todo lo que se entrega se publica automáticamente** en el Marketplace. El hackathon termina el domingo, pero el producto puede seguir vendiéndose después.
- **Encuentro presencial:** viernes 20, 9:00 a. m. a 5:00 p. m. (Costa Rica), WeWork Plaza Real Cariari, patrocinado por RACSA. Cupos limitados y RSVP aparte. Es opcional.

Implicaciones:
- El producto debe **poder venderse**, no solo mostrarse: importan el precio, quién compra y cómo se entrega.
- Los compradores son **builders y empresas**. Eso suma un posible cliente que no estaba en el análisis: agencias, integradores y desarrolladores que revenden o integran herramientas de seguridad.
- Un producto que procesa correo y se vende públicamente tiene responsabilidades (términos, privacidad, verificación de Google). Ver `docs/NEGOCIO_Y_PROBLEMA.md`.

### Preguntas para los organizadores (sobre el Marketplace)
- [ ] ¿Cómo se cobra y cómo se entrega un producto (suscripción, licencia, enlace a una app, descarga)? ¿Puedo fijar y cambiar el precio? Hoy aparece como "Free".
- [ ] ¿Quién procesa los pagos y los impuestos? ¿Cómo se paga a quien vive fuera de Costa Rica (Panamá)?
- [ ] ¿Qué obligaciones tengo como capitán (soporte, disponibilidad, mantenimiento)? ¿Puedo retirar el producto?
- [ ] ¿Qué datos de los compradores recibo y cómo debo tratarlos?
- [ ] ¿Qué licencia le doy a Dojo sobre mi proyecto?
- [ ] ¿Se puede publicar una herramienta que usa APIs de terceros con restricciones (como Gmail)? ¿Hay políticas de contenido?
- [ ] ¿Se confirma el 85 % "para siempre" y en qué condiciones?

## Kickoff del 19 de noviembre (láminas de la reunión en vivo de Dojo)
Fuente: capturas de las láminas 10 a 13 del kickoff, compartidas por la persona participante. Autor de las láminas de entrega: Daniel Bejarano (19 nov 2026).

### Cómo evalúa el jurado (lámina 11)
| Build for Builders | Peso | Build for Business | Peso |
|---|:--:|---|:--:|
| Utilidad real para otros builders | 30 % | Claridad y tamaño del problema | 30 % |
| Potencial de venta en el Marketplace | 25 % | Que la solución funcione (demo real) | 25 % |
| Calidad técnica y que funcione | 25 % | Potencial de negocio y monetización | 25 % |
| Documentación y facilidad de instalación | 20 % | Experiencia de usuario | 20 % |

### Premios (lámina 12)
- **$500 por track:** 1.er lugar **$300**, 2.º lugar **$200**. Total $1 000 (para 4 equipos).
- **85 %** de cada venta en el Dojo Marketplace es del creador; el producto sigue vendiéndose después del domingo.
- Aviso de Dojo: "Participar no garantiza ventas, inversión, contratación ni una alianza comercial." El jurado evalúa el 23 de noviembre y los resultados se publican en la página.

### Qué entregar y cuándo (lámina 10)
- **OBLIGATORIO: repositorio** con un README que cualquiera pueda seguir:
  1. **Qué hace y para quién** (el problema en dos líneas).
  2. **Cómo correrlo** (instalación y pasos, sin adivinar).
  3. **Cómo usaste agentic coding**: herramientas, flujo y archivos en el repo (`PRD.md`, `docs/adr/`, `CLAUDE.md`).
- **OBLIGATORIO: pitch deck** que cuente el problema, la solución y la demo.
- **OPCIONAL: video demo.** "Suma, pero no es requisito."
- **Deadline: domingo 22, 11:59 p. m. hora de Costa Rica (UTC−6). Sin tiempo extra.** En Panamá es 12:59 a. m. del lunes 23.
- **En el formulario de Dojo:** enlaces al repositorio y al deck. El video tiene su propio campo. **No hay un campo aparte para contar el agentic coding:** va en el README, con un resumen en la descripción.
- Al entregar, **se publica en Dojo Marketplace.**
- Clave: **buena documentación.**

### Distribución como código (lámina 13)
Flujo sugerido: Construí → **Publicá** (listing con landing y pricing claros) → Lanzá (onboarding simple y post de lanzamiento) → Primeras ventas (uno por uno) → Itera. Se pueden subir y vender: servidores MCP, plugins y skills, agentes, repos y templates, apps y micro SaaS.

### Consecuencias para Atalaya
- El **repositorio debe poder enlazarse** y ser seguible por cualquiera: será público al entregar (sin claves).
- Hay que dejar evidencia del flujo con IA en el repositorio: `PRD.md`, `docs/adr/` (decisiones de arquitectura) y `CLAUDE.md`, y resumirlo en el README y en la descripción de Dojo. `docs/USO_DE_IA.md` sirve de base.
- **El video es opcional.** Se graba solo si sobra tiempo; no es prioridad.
- **El listing necesita "pricing claro":** hace falta un precio hipotético razonado.
- El deadline es duro: sin prórroga.
- Se mantiene **Build for Business** (problema 30 %, demo 25 %, negocio 25 %, UX 20 %), salvo que cambie lo aprendido en las entrevistas. En **Build for Builders** pesarían más la calidad técnica y la documentación (45 % entre ambas) y la utilidad para otros builders.

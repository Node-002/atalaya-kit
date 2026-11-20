# Cronograma por criterios de evaluación — Atalaya (hora de Panamá)

> Complementa `docs/CRONOGRAMA.md` (hora por hora). Aquí se organiza por **qué puntúa**.
> Cierre oficial: dom 22, 11:59 p. m. Costa Rica. Meta propia: entregar dom 21:30–22:00.

| Criterio | Peso | Qué verá el jurado | Entregable que lo prueba |
|---|---|---|---|
| **A. Claridad del problema** | 30 % | A quién duele, cuánto, y que lo validaste con personas reales | Primera lámina del pitch + sección "Qué hace y para quién" del README + citas de entrevistas |
| **B. Demo real y funcional** | 25 % | Que funciona de punta a punta y que ellos mismos pueden probarlo | Enlace público en modo demo + métricas sobre ~30 correos |
| **C. Negocio** | 25 % | Quién paga, cuánto, por qué, cómo se vende | Láminas de negocio + precio del listing en el Marketplace |
| **D. Experiencia de usuario** | 20 % | Que un administrador sin conocimientos técnicos lo entiende en 30 segundos | Panel claro, textos en español sencillo, accesibilidad |

**Orden de ataque:** primero **B** (es la columna vertebral y desbloquea D), con **A** en paralelo (entrevistas y datos corren en tiempos muertos), luego **D**, y **C** al final con lo aprendido. Lo que no se recorta nunca: recorrido completo, modo demo, pitch con problema y negocio, repo limpio.

---

## Vista rápida por bloque

| Bloque | A Problema | B Demo | C Negocio | D UX |
|---|---|---|---|---|
| **Vie 10:00–14:00** | Mensajes a entrevistados pendientes | Arranque, API mínima, modo demo, login Google | — | — |
| **Vie 14:00–23:00** | Entrevistas (llamadas en pausas) | Reglas de análisis, pruebas, motor de decisión, recorrido de punta a punta | — | Panel básico sobre datos de ejemplo |
| **Sáb 08:00–13:00** | Notas y citas | Explicación con IA, aprobación humana, auditoría | Hipótesis de precio | Flujo de aprobación y estados |
| **Sáb 13:00–19:00** | Cifras del problema con fuente | Modo demo público, métricas, revisión de seguridad | Costo por buzón medido | Textos, accesibilidad, pruebas con una persona |
| **Sáb 19:00–23:00** | — | Despliegue y prueba del enlace | Precio y ventas (opciones A/B/C) | Aviso de privacidad visible |
| **Dom 08:00–12:00** | Citas al pitch | Pulir, pruebas completas, claude-security una vez | Láminas de negocio | Último repaso de usabilidad |
| **Dom 12:00** | **Congelar funciones** | | | |
| **Dom 13:00–20:00** | Pitch final | README probado desde cero, repo público | Listing en Marketplace | — |
| **Dom 21:30–22:00** | **Submit and publish** (enlaces probados en ventana privada) | | | |

---

## A. Claridad del problema (30 %) — la que más pesa

**Primero (viernes, desde ya):**
1. Escribir a quienes no han respondido (una consultora de TI, una universidad privada) y llamar a una universidad pública (soporte MFA) en horas de oficina. Meta: **al menos 3 conversaciones**, aunque sean de 10 minutos con conocidos que tengan un negocio pequeño.
2. Usar `docs/HOJA_ENTREVISTA.md`. Anotar solo lo esencial, sin datos personales de nadie.

**Después (sábado):**
3. Pasar las notas a `docs/NEGOCIO_Y_PROBLEMA.md`: qué dolor se repite, qué ya usan, qué pagarían.
4. Reunir 2 o 3 cifras del problema **con fuente verificada** (no inventar). Si no hay fuente, decirlo como hipótesis.
5. Definir el cliente en una frase: "administrador de una organización pequeña de Panamá/Costa Rica sin equipo de seguridad".

**Cómo:** una historia, no una lista: persona → situación → pérdida → por qué las soluciones actuales no le sirven.
**Listo cuando:** la primera lámina se entiende en 20 segundos y hay al menos una cita real.

---

## B. Demo real y funcional (25 %) — se construye primero

**Primero (viernes 10:00–14:00):**
1. Rama de trabajo, `CLAUDE.md` (`init`), `PRD.md` (`write-spec`), `docs/adr/0001` (`architecture`), `.env.example`, commit "inicio del hackathon".
2. FastAPI con `/health`, modelos pydantic del contrato y `DemoProvider` con 3 correos. Primer recorrido de punta a punta con datos simulados.
3. Login de Google y lectura de 5 correos. **Corte duro 14:00:** si falla, Plan B (entrada manual).

**Después:**
4. (Vie tarde) Reglas: SPF/DKIM/DMARC, dominios parecidos, remitente vs. respuesta, acortadores, urgencia. Pruebas con `testing-strategy`.
5. (Vie noche) Motor de decisión y etiquetas. **Hito: recorrido completo, aunque feo.**
6. (Sáb mañana) Explicación con IA (correo = dato hostil, JSON validado, datos enmascarados), aprobación humana, auditoría.
7. (Sáb tarde) Modo demo público completo y **script que mide aciertos y falsos positivos** sobre los 30 correos.
8. (Sáb 17:00) Revisión de seguridad: gitleaks, bandit, pip-audit, `security-review`.
9. (Sáb noche) **Despliegue** y prueba del enlace público. No dejarlo para el domingo.

**Cómo:** la IA implementa, vos revisás cada cambio y probás a mano. Un commit por avance.
**Listo cuando:** alguien ajeno abre el enlace, ve un correo sospechoso, entiende por qué, y aprueba la cuarentena sin ayuda.

---

## D. Experiencia de usuario (20 %)

**Primero (viernes noche):** panel básico con la bandeja simulada, para que el recorrido sea visible.

**Después (sábado):**
1. Pantallas de alerta y detalle: riesgo en un color **y** un texto (no solo color), explicación en español sencillo, botón claro de aprobar/rechazar.
2. `design:ux-copy` para los textos; `design:accessibility-review` para contraste, teclado y etiquetas.
3. **Prueba con una persona real** (familiar o amigo): si no entiende sin explicación, se simplifica.
4. Aviso de privacidad visible y estados claros (cobertura activa/revocada).

**Cómo:** menos pantallas, un solo camino principal, nada de jerga ("SPF" → "el remitente no pudo comprobar que es quien dice ser").
**Listo cuando:** una persona sin conocimientos completa el recorrido en menos de 2 minutos.

---

## C. Negocio (25 %)

**Primero (sábado mañana):** con lo aprendido en las entrevistas, definir quién paga y por qué. Hipótesis de precio razonada, no inventada.

**Después:**
1. (Sáb tarde) Medir el **costo real por buzón** (tokens por correo en las pruebas) para el margen del pitch. Verificar precios vigentes con `claude-api`.
2. (Sáb noche) Elegir la oferta del Marketplace: A (servicio por buzón), B (kit autoalojado) o C (motor como herramienta). Recordar que la app pública solo funciona en modo demo.
3. (Dom mañana) Láminas de negocio: cliente, precio, costo, canal de venta (85 % para vos), siguiente paso.
4. (Dom tarde) Completar el listing con precio claro. Confirmar en Discussions el flujo de cobro si sigue sin respuesta.

**Listo cuando:** el pitch responde "¿quién paga, cuánto y por qué ahora?" con un número respaldado.

---

## Pitch y entrega (domingo)
| Hora | Tarea |
|---|---|
| 08:00–12:00 | Pulir, pruebas completas, citas al pitch, claude-security **una vez** |
| 12:00 | **Congelar funciones** |
| 13:00–16:00 | Pitch con enlace público (orden: problema → demo → negocio → UX → siguiente paso) |
| 16:00–18:00 | Video de 2–3 min **solo si sobra tiempo** (opcional) |
| 19:00–20:00 | README probado desde cero; repo público **después de gitleaks** |
| 20:00 | Cargar enlaces en Dojo; probar todo en ventana privada |
| 21:30–22:00 | **Submit and publish** y captura de la confirmación |

## Si vas atrasado, recortar en este orden
1. Estado de cobertura ampliado · 2. Auditoría detallada · 3. Conector Microsoft · 4. Reputación de enlaces y hash de adjuntos · 5. Lecciones y alertas por Telegram.

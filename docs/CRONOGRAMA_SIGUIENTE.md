# Cronograma: de ahora hasta la entrega

> Hora de Panamá (UTC-5). Entrega oficial: domingo 22 nov, 11:59 p. m. de Costa Rica (UTC-6, es decir 12:59 a. m. del lunes en Panamá). **Tu meta propia: enviar antes de las 10:00 p. m. del domingo.** Bloques de 90 minutos con pausa de 15 y dormir a las 10 u 11 p. m., como dijiste.
> Marca **[tú]** lo que solo puedes hacer tú y **[yo]** lo que puedo hacer yo. Si un paso se atrasa, lo que va marcado como **mínimo** es lo que no puede faltar.

## Sábado 21 de noviembre

### Bloque 1 (5:30 a 7:00) Revisar y decidir
| Orden | Qué | Quién | Mínimo |
|---|---|---|---|
| 1 | Leer `docs/INFORME_NOCHE_20_NOV.md` (10 min) | tú | sí |
| 2 | Mirar la demo de la rama `integracion` y probar la campaña y el botón de supervisor (10 min) | tú, con mi ayuda | sí |
| 3 | Decir «aceptado» o qué cambiar. Yo fusiono en `hackathon/mvp`, corro `gitleaks` y subo | tú decides, yo ejecuto | sí |
| 4 | Revisar los dominios oficiales de las marcas (propongo la lista, tú confirmas) | los dos | recomendado |

### Bloque 2 (7:15 a 8:45) Despliegue público (el mayor riesgo, por eso va primero)
| Orden | Qué | Quién | Mínimo |
|---|---|---|---|
| 5 | Crear cuenta en Render (o Railway) y conectar el repositorio privado | tú | sí |
| 6 | Seguir `docs/DESPLIEGUE.md`. Imagen Docker **sin probar**: reserva 60 min para el primer error de arranque | los dos | sí |
| 7 | Abrir el enlace en **ventana privada** y desde el celular con datos; comprobar `/health` (`mode: demo`) y que `/auth/google/login` da «Not Found» | tú | sí |
| 8 | Poner `ATALAYA_BASE_URL` con la URL real y redesplegar | tú | sí |

### Bloque 3 (9:00 a 10:30) Evidencia
| Orden | Qué | Quién | Mínimo |
|---|---|---|---|
| 9 | **9:00 llega el recordatorio del reloj de Windows:** sincronizarlo (Configuración > Hora e idioma > Sincronizar ahora) | tú | sí |
| 10 | Publicar la encuesta con la cuenta del proyecto (`docs/ENCUESTA_DOJO.md`), probarla en ventana privada y compartirla en Dojo y grupos | tú | sí |
| 11 | Enviar 1 o 2 mensajes de entrevista (`docs/PLAN_ENTREVISTAS_SABADO.md`). Si no hay respuesta, la encuesta y la evidencia pública son el plan B | tú | recomendado |

### Bloque 4 (10:45 a 12:15) Calidad de detección
| Orden | Qué | Quién |
|---|---|---|
| 12 | Decidir si añado señal para enlaces a IP y correos sin cabecera de autenticación (cambia la calibración; lo mido antes y después) | los dos |
| 13 | Probar con tu Gmail real los correos mínimos de `docs/CORREOS_DE_PRUEBA_REALES.md` (A1, A2, B1, B2, C1, C2, D1, G1, N1) contra la app local con Gmail | tú |
| 14 | Actualizar `docs/RESULTADOS_PRUEBAS.md` con lo que salga | yo |

**Almuerzo y descanso (12:15 a 1:30).**

### Bloque 5 (1:30 a 3:00 p. m.) Pitch
| Orden | Qué | Quién | Mínimo |
|---|---|---|---|
| 15 | Borrador del guion y de las diapositivas (problema, demo, negocio, límites honestos) con `docs/PITCH.md` y `docs/EVIDENCIA_PUBLICA.md`. Citar cifras solo después de abrir la fuente | yo redacto, tú revisas | sí |
| 16 | Resultados de la encuesta (cuántas respuestas y de quiénes, sin redondear) | los dos | sí |

### Bloque 6 (3:15 a 4:45 p. m.) Opcionales según tiempo
- Comprar saldo de la API y probar la IA real (verificar nombre del modelo, costo por correo y correr el corpus con `ATALAYA_LLM=anthropic`). **[tú]** compras, **[yo]** pruebo.
- Pulir lo que te haya molestado de la interfaz al probarla.
- Dos buzones reales de Google para probar campañas con Gmail real (solo si puedes crear una segunda cuenta de prueba tú mismo).

### Cierre del sábado
- 5:00 p. m. a 6:00 p. m.: respaldo (`git push` de la rama, con tu sí) y lista de pendientes para el domingo.
- Descanso y dormir temprano.

## Domingo 22 de noviembre

### Bloque 1 (6:00 a 7:30) Entregables obligatorios
| Orden | Qué | Quién | Mínimo |
|---|---|---|---|
| 1 | README final: qué es, para quién, cómo correrlo (probado desde cero en una carpeta nueva) y cómo se usó la programación con IA | yo redacto, tú revisas | sí |
| 2 | Actualizar `docs/USO_DE_IA.md` con lo de esta noche y las decisiones tuyas | yo | sí |
| 3 | Revisión de seguridad final: `pytest`, `ruff`, `bandit`, `pip-audit` y `gitleaks` sobre **todo el historial** | yo | sí |

### Bloque 2 (7:45 a 9:15) Pitch final
| Orden | Qué | Quién | Mínimo |
|---|---|---|---|
| 4 | Presentación con enlace público (no archivo local) | los dos | sí |
| 5 | Ensayo del recorrido de demo de 2 a 3 minutos: panel, campaña, aprobar con motivo, informe, supervisor | tú | sí |
| 6 | Video corto grabando ese recorrido | tú | opcional |

### Bloque 3 (9:30 a 11:00) Publicar el repositorio y probar todo
| Orden | Qué | Quién | Mínimo |
|---|---|---|---|
| 7 | Revisar el historial por secretos. Si gitleaks queda limpio, **hacer público el repositorio** (solo entonces) | los dos | sí |
| 8 | Probar **todos** los enlaces de la entrega en ventana privada: demo, repositorio, presentación, video, encuesta | tú | sí |
| 9 | Abrir la demo justo antes de enviar (el plan gratuito se duerme) | tú | sí |

### Bloque 4 (a partir de 11:30) Envío con margen
- Mediodía: relectura final del formulario de entrega con mis comentarios.
- **Antes de las 10:00 p. m.: «Submit and publish».** Solo después de probar todos los enlaces. Si algo falla, el margen hasta la hora oficial es de casi 3 horas.

## Orden de prioridad si falta tiempo
1. Demo pública funcionando (el despliegue).
2. Encuesta publicada y pitch con límites honestos.
3. README y repositorio limpio.
4. Marcas verificadas y detección mejorada.
5. IA real, dos buzones reales, video y animaciones extra.

## Riesgos y cómo evitarlos
| Riesgo | Qué hacer |
|---|---|
| La imagen Docker falla al construir en Render | Dejar el despliegue para el sábado por la mañana; si falla, me pasas el registro y lo arreglo. |
| Los tokens de Google caducan a los 7 días | Reconectar la cuenta de prueba antes de grabar o presentar. |
| Reloj de Windows desfasado (falló el primer login) | Sincronizarlo a las 9:00 del sábado y antes de grabar. |
| La demo gratuita está «dormida» al abrirla el jurado | Abrirla justo antes de enviar y avisar en el pitch. |
| Se cita una cifra mal | Abrir la fuente antes de citarla; no mezclar estudios distintos. |

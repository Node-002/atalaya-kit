# ADR 0002 — Explicación con IA: dato hostil, vocabulario cerrado y "solo sube el riesgo"

- **Fecha:** 2026-11-20
- **Estado:** aceptada (implementada con explicador simulado; llamada real pendiente de crédito de API)

## Contexto
Las reglas por código (SPF/DKIM/DMARC, dominios parecidos, enlaces, urgencia) no detectan fraudes de significado: fraude de factura, fraude del jefe, enlace a un sitio desconocido (ver `docs/RESULTADOS_PRUEBAS.md`: 3 de 14 phishing no detectados). Una IA puede ayudar, pero el correo es **contenido controlado por un atacante** que puede traer instrucciones dirigidas al propio modelo.

## Decisión
1. **El correo es dato, nunca instrucciones.** Va entre etiquetas con un nonce aleatorio por llamada; se elimina cualquier intento de cerrar o abrir esa etiqueta. La IA no recibe herramientas.
2. **Minimización y privacidad.** Se envía: dominio del remitente (no la dirección), asunto y texto recortados (200 / 1 500 caracteres), solo los dominios de los enlaces y las señales ya calculadas. Teléfonos, cédulas, tarjetas, números largos y correos se enmascaran antes de enviar.
3. **Salida validada.** JSON con `explanation` (≤ 500 caracteres) y `semantic_flags` de un **vocabulario cerrado** (`payment_change_request`, `secrecy_pressure`, `credential_request`, `unknown_login_link`). Cualquier otra cosa se descarta y se usa la plantilla de reglas.
4. **La IA solo puede subir el riesgo.** Sus banderas se convierten en señales con **pesos fijados por el código** y un **tope de 50 puntos**: por sí sola puede llevar un correo a riesgo *medio* (etiqueta "Revisar"), nunca a *alto* (cuarentena). La aprobación humana sigue siendo obligatoria para aislar. Una respuesta tipo "es seguro" no baja nada.
5. **Costo.** Política `flagged` (por defecto): solo riesgo medio/alto. `all`: todos los correos (detecta los fraudes que las reglas dejan en bajo, pero cuesta más). Una llamada por correo (caché), modelo ligero, `max_tokens` 400, tiempo límite 20 s.
6. **Degradación.** Si falla la red, el saldo o la validación, se usa la plantilla de reglas; el sistema nunca deja de funcionar por la IA.
7. **Honestidad en la interfaz.** Cada alerta indica el origen del resumen: `rules`, `ai` o `simulated` (rotulado "sin IA real").
8. **Demo pública:** usa el explicador simulado, para que visitantes no puedan gastar saldo. La clave real solo se usa en local, activando `ATALAYA_LLM=anthropic`.

## Estado de la verificación
- Probado con un **cliente falso** (sin red): análisis de la respuesta, tope de tokens, ausencia de herramientas, degradación ante error.
- **No probado** contra la API real (sin crédito al momento de escribir esto) ni medido su efecto sobre los 30 correos.
- El explicador simulado usa palabras clave y **no representa el rendimiento de un modelo**; no debe citarse como resultado de IA.

## Alternativas descartadas
- **Que la IA decida el riesgo:** vulnerable a inyección de prompt y no auditable.
- **Dejar que la IA ponga los pesos:** permitiría manipular la puntuación desde el contenido del correo.
- **Llamar a la API en la demo pública:** cualquiera podría consumir el saldo.

## Seguimiento
Cuando haya crédito: verificar el nombre del modelo, medir tokens por correo, correr el corpus con `ATALAYA_LLM=anthropic` (y política `all`) y registrar el efecto real sobre P06, P08, P13 y sobre los falsos positivos.

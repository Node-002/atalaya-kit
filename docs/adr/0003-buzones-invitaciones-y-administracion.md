# ADR 0003 — Varios buzones, invitaciones de un solo uso y rol de administración

- **Fecha:** 2026-11-20
- **Estado:** aceptada. Implementada para Gmail (uso local, usuarios de prueba) y para la demo pública (simulada).

## Contexto
En una empresa, **quien usa Atalaya y quien tiene el correo son personas distintas**: una persona (administración) vigila el phishing de varios buzones; cada empleado es dueño del suyo. El diseño inicial asumía un solo buzón y que quien abría el panel era quien iniciaba sesión con Google. Eso no sirve para vender a organizaciones.

## Decisión
1. **Dos roles.** *Administración*: entra al panel con contraseña, ve alertas y decide. *Dueño del buzón*: solo recibe un enlace, lo autoriza con Google y ve una confirmación; **nunca ve el panel ni las alertas**.
2. **Invitación de un solo uso.** La administración crea un enlace con un nombre o puesto; token aleatorio (256 bits), **solo se guarda su hash SHA-256**, vence a las 48 h, se puede revocar y se marca como usado de forma atómica. El token se muestra una única vez.
3. **Consentimiento informado, visible y obligatorio.** Antes de ir a Google, la persona lee qué hace Atalaya, qué ve la administración, qué NO hace, qué permiso mostrará Google y cómo retirarlo; debe marcar una casilla. El servidor exige `consent=1` y registra `consent_at`. No se permite saltar esa página: es una obligación ética y probablemente legal (ver `docs/ETICA_LEGAL_SEGURIDAD.md`, sección de Panamá, sin verificar).
4. **Autorización con Google, sin contraseñas.** OAuth con `state` ligado a cookie y PKCE. El `state` queda atado a la invitación, de modo que el buzón se registra en la organización de quien invitó. Si la invitación se revoca o vence durante el proceso, el acceso no se conserva y se revoca en Google.
5. **Registro de buzones en SQLite.** Tokens OAuth **cifrados con Fernet** por buzón; reconectar el mismo correo actualiza el token, no duplica. No se guardan cuerpos ni adjuntos. Las alertas siguen en memoria.
6. **Administración protegida.** Contraseña por variable de entorno (mínimo 12 caracteres; sin ella **el modo conectado no arranca**), sesión en cookie firmada `HttpOnly`/`SameSite=Lax` de 8 h, **límite de 5 intentos fallidos cada 5 minutos**, CSRF por cabecera personalizada en toda escritura, y toda la API (salvo `/api/public/*`) exige sesión.
7. **Auditoría persistente.** Se registra: inicios de sesión (éxito, fallo, bloqueo), invitaciones creadas/revocadas, buzones conectados/reconectados/desconectados.
8. **Desconectar revoca.** Quitar un buzón desde el panel revoca el token en Google y borra el registro local; el dueño también puede retirarlo desde su cuenta de Google.
9. **Demo pública.** Misma lógica con buzones simulados: 3 empleados (el mismo phishing llega a dos) y el flujo de invitación completo contra una conexión simulada, sin Google. Sin login (datos ficticios, sin cuentas reales).

## Lo que NO resuelve (límites reconocidos)
- **Google en modo de pruebas:** solo cuentas registradas como usuarios de prueba (máx. 100) y tokens que caducan a los 7 días. Para uso público haría falta la verificación de Google y una evaluación de seguridad externa.
- **Cuentas de empresa (Google Workspace):** el administrador de TI puede bloquear apps de terceros y la persona vería "acceso bloqueado". En ese caso hace falta que TI autorice la app. Para empresas medianas, el camino real es la **delegación a nivel de dominio** (un solo consentimiento del superadministrador cubre todos los buzones): **no está construida**, queda como siguiente paso.
- **Microsoft 365:** no implementado.
- **Una sola organización** por instalación y **una sola persona administradora** (sin roles ni usuarios múltiples).
- **Alertas persistentes desde el 20 nov (tarde):** en modo conectado se guardan **cifradas** (Fernet) en SQLite, sin cuerpos ni adjuntos, para que un correo puesto en cuarentena —que sale de la bandeja y Atalaya ya no vuelve a leer— se pueda devolver aunque se reinicie el servidor. Al desconectar un buzón se borran sus alertas. Los mensajes de Gmail se identifican por su ID (no es contenido). El texto del resumen puede contener fragmentos generados por la IA a partir del correo, ya enmascarados y recortados.
- **Sin agrupación por campaña:** el mismo phishing en varios buzones aparece como alertas separadas.
- **La sesión de administración es por contraseña única**, sin segundo factor.

## Alternativas descartadas
- **Que cada empleado cree una cuenta en Atalaya:** más fricción y más datos personales almacenados.
- **Que el empleado vea sus propias alertas:** fuera del alcance; se puede agregar después.
- **Saltar el consentimiento y dejar solo la pantalla de Google:** esa pantalla no explica quién verá los avisos ni lo que Atalaya hace con ellos.
- **Guardar el token de invitación para poder reenviarlo:** habría que guardarlo en claro; se prefiere crear otro.

## Verificación
90 pruebas, entre ellas: un solo uso y vencimiento de la invitación, token no almacenado en claro (también en el archivo de la base), tokens OAuth cifrados y ilegibles con otra clave, rechazo de consentimiento ausente, API cerrada sin sesión, cookie falsificada, límite de intentos, arranque rechazado sin contraseña o con una débil, CSRF, aislamiento de acciones entre buzones, y recorrido completo de invitación en la demo. **No probado:** el intercambio real con Google desde una invitación (requiere iniciar sesión con una cuenta de prueba).

## Actualización (20 nov, noche): decisiones con motivo escrito e informe por correo
**Contexto.** Cuarentena y "sacar de cuarentena" eran decisiones sin justificar, y el panel mezclaba "revisado por una persona" con "nunca fue sospechoso". Con falsos positivos inevitables, una empresa necesita saber *quién* decidió, *cuándo* y *por qué*.

**Decisión.**
1. **Motivo escrito (mínimo 10 caracteres, máximo 500) obligatorio cuando la decisión va más allá o en contra de Atalaya:** sacar un correo de cuarentena, aislar uno que Atalaya *no* marcó como alto, dejar sin aislar uno que sí marcó como alto, y marcar como legítimo uno señalado. **Aislar lo que Atalaya ya marcó como alto es un clic** (el análisis de Atalaya queda como razón; el motivo es opcional) para no frenar la respuesta en un incidente.
2. **El servidor valida el motivo antes de tocar el correo:** sin motivo válido no cambia nada en Gmail (error 422).
3. **Estado "revisado":** una persona ya decidió. Los correos revisados van a su propio grupo, separados de "Sin riesgo" (lo que Atalaya nunca vio sospechoso), y conservan el riesgo original visible.
4. **Historial por correo** con hora, quién, decisión y motivo; y **un informe por correo** (`GET /api/alerts/{id}/report`, texto Markdown): qué detectó Atalaya (señales y puntos), las decisiones humanas con su motivo, y el resultado. **No incluye el contenido del correo** ni adjuntos.
5. Los motivos se guardan **cifrados** junto con la alerta; no se copian a la auditoría general (que está en claro), para no filtrar texto escrito por personas.

**Límites.** El motivo es texto libre y confiable solo en la medida en que lo sea la persona que lo escribe: no hay firma ni segundo aprobador. El informe es texto plano, no un PDF. Atalaya **no aprende** de estas decisiones (no hay lista de remitentes de confianza): se deja como siguiente paso, por el riesgo de suplantación.

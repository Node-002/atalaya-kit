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
- **Alertas en memoria:** se pierden al reiniciar y se recalculan desde la bandeja.
- **Sin agrupación por campaña:** el mismo phishing en varios buzones aparece como alertas separadas.
- **La sesión de administración es por contraseña única**, sin segundo factor.

## Alternativas descartadas
- **Que cada empleado cree una cuenta en Atalaya:** más fricción y más datos personales almacenados.
- **Que el empleado vea sus propias alertas:** fuera del alcance; se puede agregar después.
- **Saltar el consentimiento y dejar solo la pantalla de Google:** esa pantalla no explica quién verá los avisos ni lo que Atalaya hace con ellos.
- **Guardar el token de invitación para poder reenviarlo:** habría que guardarlo en claro; se prefiere crear otro.

## Verificación
90 pruebas, entre ellas: un solo uso y vencimiento de la invitación, token no almacenado en claro (también en el archivo de la base), tokens OAuth cifrados y ilegibles con otra clave, rechazo de consentimiento ausente, API cerrada sin sesión, cookie falsificada, límite de intentos, arranque rechazado sin contraseña o con una débil, CSRF, aislamiento de acciones entre buzones, y recorrido completo de invitación en la demo. **No probado:** el intercambio real con Google desde una invitación (requiere iniciar sesión con una cuenta de prueba).

# Revisión de seguridad — panel de administración e invitaciones (20 nov 2026)

> Revisión hecha por el desarrollador con ayuda de IA, **no es una auditoría independiente ni una prueba de penetración**. Cada punto se verificó con una prueba automática o ejecutando el servidor.

## Resultados
| Pregunta | Resultado | Cómo se verificó |
|---|---|---|
| ¿Hay contraseñas o claves en el código que llega al navegador? | **No.** La contraseña de administración vive solo en `.env` y en memoria del servidor (como SHA-256). Ninguna respuesta la repite. | Búsqueda en `app/static/` + prueba que recorre esos archivos + prueba que revisa las respuestas de login, `/health`, `/api/me`, `/api/audit` |
| ¿Se guarda una contraseña intentada? | **No**, ni en la auditoría. | Prueba |
| ¿Hay límite de intentos? | **Sí:** 5 fallos cada 5 minutos por dirección, y bloquea incluso la contraseña correcta mientras dure. Cuerpos mal formados cuentan como fallo y no tumban el servidor. | Pruebas |
| ¿Se puede copiar una cookie de sesión y seguir usándola? | **Ya no.** Cada sesión tiene un identificador en el servidor; "Salir" la invalida. | Prueba de repetición de cookie |
| ¿Quedan secretos en los registros del servidor? | **Sí quedaban (defecto encontrado y corregido):** el token de invitación, el `code` y el `state` de Google aparecían en el registro de acceso. Ahora se reemplazan por `[oculto]`. | Se reprodujo el defecto con un servidor real y se repitió tras el arreglo |
| ¿La cookie del flujo de Google respeta HTTPS? | **Corregido:** era `secure=False` fijo; ahora depende de si la URL de redirección es https. | Revisión de código |
| ¿Se aceptan cuentas con letras de otros alfabetos (homógrafos)? | **No.** Al conectar un buzón se exige una dirección ASCII normal; con cirílico, griego, acentos o dominio en punycode se rechaza, se revoca el token y se deja constancia. | 6 pruebas |

## Otras medidas ya presentes
Contraseña de mínimo 12 caracteres (si falta o es débil, el modo conectado no arranca); cookie `HttpOnly` y `SameSite=Lax`; protección CSRF por cabecera en toda escritura; toda la API cerrada sin sesión (salvo `/api/public/*`); `Cache-Control: no-store` en la API; `Referrer-Policy: no-referrer` (el token de invitación no viaja a Google ni a terceros); CSP `default-src 'self'` sin scripts en línea; contenido de correos solo con `textContent`; tokens OAuth cifrados con Fernet; el enlace de invitación se guarda solo como hash.

## Límites conocidos (no resueltos)
- **Una sola contraseña compartida para administración:** sin responsabilidad individual (la auditoría dice "administrador"), sin forma de revocar a una persona, sin segundo factor. Recomendación: iniciar sesión con Google para administradores (ver abajo).
- **Límite de intentos por dirección y en memoria:** se reinicia al reiniciar el servidor; detrás de un proxy todas las personas comparten dirección; un atacante puede bloquear a la persona administradora (denegación de acceso).
- **Sesiones en memoria:** reiniciar el servidor cierra todas.
- **El token de invitación va en la URL** (queda en el historial del navegador de quien lo abre). Mitigaciones: un solo uso, vence en 48 h, revocable, sin referente, fuera de los registros.
- **El permiso de Gmail (`gmail.modify`) es más amplio que el uso** que hace el código (permite técnicamente enviar y crear borradores). La garantía es del código, no del permiso, y se dice en la página de consentimiento.
- **HTTPS:** localmente es HTTP. En el despliegue hay que usar HTTPS y fijar `ATALAYA_BASE_URL` con `https://` para que las cookies sean `Secure`.
- **No evaluado:** pruebas de penetración, comportamiento tras un proxy inverso, ataques de denegación de servicio, comparación con la lista oficial completa de Unicode (la tabla de confusables es parcial).

## Propuesta pendiente de decisión: administradores con "Iniciar sesión con Google"
No crear un sistema propio de usuarios y contraseñas. En su lugar:
1. Las personas administradoras entran con su cuenta de Google (OpenID Connect). Atalaya **no guarda contraseñas de administradores**; Google se ocupa de recordarla, del segundo factor y de recuperarla.
2. Lista de correos autorizados (primero por variable de entorno; luego, un administrador puede añadir a otro desde el panel). Opcionalmente, solo del dominio de la empresa (`hd`).
3. Validar el token de identidad (firma, emisor, audiencia, vencimiento, correo verificado) y comparar el correo ya normalizado y con la misma regla ASCII que usamos para los buzones.
4. La auditoría pasa a registrar **quién** hizo cada cosa.
5. Quitar a alguien de la lista le revoca el acceso.

Requisitos: agregar los permisos básicos `openid` y `email` en la pantalla de consentimiento de Google (no son sensibles) y que cada administrador sea usuario de prueba mientras la app esté en modo de pruebas.

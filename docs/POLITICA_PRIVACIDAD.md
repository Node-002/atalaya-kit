# Política de privacidad de Atalaya (BORRADOR)

> ⚠️ **Borrador no revisado por una persona abogada.** Describe lo que hace el código del repositorio a fecha 21 nov 2026. No es asesoría legal ni cumple por sí sola ninguna ley (por ejemplo, la ley de protección de datos personales de Panamá o la de Costa Rica). Antes de usarlo con personas reales hay que revisarlo y completar los puntos marcados **[POR DEFINIR]**.

**Responsable de los datos:** en el kit autoalojado, **la organización que lo instala**: decide qué buzones conecta, guarda los datos en su propio servidor y responde por su tratamiento; el equipo Atalaya (una persona) no los recibe ni los custodia. En la demo pública, el equipo Atalaya es quien la opera y no hay datos reales. **[Confirmar con revisión legal]**. **Contacto:** [POR DEFINIR: correo de contacto].
**Última actualización:** 21 nov 2026.

## 1. En resumen
- Atalaya lee tus correos **nuevos** para avisar si alguno parece phishing o fraude.
- **No guarda el cuerpo de tus correos ni sus adjuntos.**
- Guarda solo el resultado del análisis: veredicto, señales, un identificador (hash) y el estado de la decisión.
- Nunca borra ni envía correos. Puede etiquetar y, si la persona administradora lo aprueba, sacar un correo de la bandeja (siempre reversible).
- La demo pública **no usa datos reales**.

## 2. Dos modos, dos situaciones
| | Demo pública | Uso real (modo Gmail) |
|---|---|---|
| Qué es | Simulación con empleados y correos inventados | Conexión de buzones reales de Google, hoy **solo en el equipo de la persona autora**, con usuarios de prueba |
| Datos personales reales | **No.** No hay inicio de sesión ni conexión con Google | Sí, ver abajo |
| Almacenamiento | Memoria, una copia por visitante; caduca a las 2 h y se pierde al reiniciar | Base de datos SQLite local |
| Cookie | `atalaya_demo_sid` (aleatoria, `HttpOnly`, `SameSite=Lax`) para separar tu copia de la de otros visitantes | Cookie de sesión de administración |
| Registros del servidor | La plataforma de alojamiento (Render) puede guardar registros técnicos, como la dirección IP; Atalaya los usa solo para limitar el ritmo de uso | Igual |

## 3. Qué datos trata (modo Gmail)
**Qué lee de Gmail:** solo la bandeja de entrada, los mensajes nuevos y los de los **últimos 7 días** al conectar. Permiso pedido a Google: `gmail.modify` («leer, redactar y enviar correos» en el texto de Google), el más pequeño que permite poner etiquetas y mover correos. Atalaya **no envía ni borra** mensajes.

**Qué guarda** (en SQLite):
| Dato | Detalle |
|---|---|
| Buzón | Nombre visible, dirección de correo, fecha del consentimiento, y el **token de acceso de Google cifrado** (Fernet) |
| Alerta (cifrada en reposo) | Veredicto y nivel de riesgo, señales detectadas, **dominio** del remitente, hora, explicación, estado, identificador/hash del mensaje, huellas (hash) para agrupar campañas, y las decisiones con quién y cuándo y el **motivo escrito** por la persona administradora |
| Invitaciones | Hash del enlace (no el enlace), fecha de vencimiento y estado |
| Auditoría y seguridad | Quién hizo qué y cuándo (por ejemplo, inicios de sesión de administración), con la dirección IP en intentos y bloqueos |

**Qué NO guarda:** cuerpos de correo, adjuntos, contraseñas, ni el remitente completo ni el asunto en las alertas (solo el dominio y huellas).

**Nota importante:** el texto del correo **sí pasa por la memoria del servidor** mientras se analiza; simplemente no se escribe en la base de datos ni en los registros (los registros ocultan tokens y códigos).

## 4. Uso de inteligencia artificial
- En la demo pública la explicación es **simulada**: no se envía nada a ningún servicio de IA.
- Si la persona administradora activa la IA real (proveedor previsto: Anthropic), Atalaya enviaría para cada correo: el **dominio** del remitente, el **asunto** (máx. 200 caracteres), los **dominios de los enlaces** y el **texto** (máx. 1 500 caracteres), **después de enmascarar** correos, cédulas, tarjetas, teléfonos y números largos.
- El enmascarado es de **mejor esfuerzo, no una garantía**: puede dejar pasar datos personales con formatos no previstos.
- La IA **no recibe herramientas** y su respuesta se valida; no decide por sí sola.
- **Esta función no se ha probado con una cuenta real de pago.** Las condiciones del proveedor de IA (por ejemplo, cuánto tiempo conserva datos) **[POR DEFINIR: revisar y citar]**.

## 5. Para qué se usan los datos
Solo para analizar el correo, mostrar alertas a la persona administradora (y a quien supervise, en solo lectura), registrar decisiones y proteger el servicio (límite de intentos). No se venden, no se usan para publicidad ni para entrenar modelos propios.

## 6. Quién ve qué
- **Administración:** ve alertas, señales, dominios, decisiones y el historial. No ve contraseñas ni el contenido completo de los correos.
- **Supervisión (solo lectura):** ve el panel y los informes, y no puede actuar (el servidor lo rechaza).
- Cada persona que conecta su buzón ve antes una pantalla de consentimiento (`/invite`) y decide si acepta.

## 7. Tus derechos y cómo retirar el acceso
- Puedes retirar el acceso en cualquier momento desde tu cuenta de Google: **Seguridad → Tus conexiones con apps de terceros → Atalaya → Quitar acceso**.
- Puedes pedir a la persona administradora que desconecte tu buzón.
- Para pedir acceso, corrección o eliminación de tus datos: [POR DEFINIR: correo de contacto y plazo de respuesta].
- **Conservación:** el código **no define** hoy un plazo de borrado automático de las alertas ni del historial. **[POR DEFINIR: plazo]**.

## 8. Seguridad
Tokens de Google y alertas cifrados en reposo (Fernet); cookies `HttpOnly` y `SameSite`; protección contra CSRF; límite de intentos con bloqueo; todo el contenido de correo se escapa en la interfaz y no se muestra HTML de correos. Ningún sistema es 100 % seguro, y no se ha hecho una prueba de intrusión independiente.

## 9. Menores y terceros
Atalaya está pensado para uso organizacional. Una organización que lo use con menores (por ejemplo, un colegio) debe cumplir sus propias obligaciones legales. **[POR DEFINIR]**.

## 10. Cambios
Si esta política cambia, se actualizará la fecha de arriba.

---
## Anexo (para la persona autora): `app/static/invite.html` frente al código
Revisado en solo lectura el 21 nov 2026; **no se editó**. Lo que dice la pantalla de consentimiento y es correcto según el código: revisa correos nuevos y los de los últimos 7 días; etiqueta y, con aprobación, saca de la bandeja de forma reversible; no borra ni envía; no guarda cuerpos ni adjuntos; no pide contraseña; cómo retirar el acceso en Google; el administrador ve dominio, hora y motivo.

Diferencias o huecos a considerar (decisión tuya):
1. **No menciona la IA externa.** Si se activa la IA real, texto enmascarado y recortado del correo se enviaría a un proveedor (Anthropic). La pantalla no lo dice. Es la omisión más importante.
2. **«No ve el contenido completo de tus correos»** puede entenderse como que ve una parte. El panel no muestra ningún cuerpo; conviene «no ve el contenido de tus correos».
3. **No dice qué sí se guarda:** veredicto, señales, dominio, hash, estado y motivos de decisión (alertas cifradas), más el token cifrado y un registro de auditoría con direcciones IP.
4. **No menciona al supervisor de solo lectura**, que también ve las alertas.
5. **No enlaza** a la política de privacidad ni a los términos, y no da un **contacto** ni un plazo de conservación (hoy no definidos).
6. «Es el permiso más pequeño que Google ofrece para poder poner etiquetas» es una afirmación técnica que esta revisión **no verificó** con la documentación de Google.

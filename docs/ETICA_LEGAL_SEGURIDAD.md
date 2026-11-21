# Ética, legalidad, seguridad y verificaciones

> **No soy abogado ni estas notas son asesoría legal.** Las leyes se mencionan para que sepas *qué consultar*.
> Verificá cada una en la fuente oficial (texto vigente) y, si el proyecto pasará a producto, con un abogado
> o con el área legal de tu universidad.

## 1. Principios éticos (tu postura profesional)
- **Consentimiento informado:** solo se conecta una cuenta si su dueño acepta, entendiendo qué se lee y para qué.
- **Mínimo necesario:** leer solo lo que se requiere, guardar solo veredicto, señales, ID, estado y una lista blanca de metadatos técnicos de cabeceras (SPF/DKIM/DMARC, IP de origen, Return-Path enmascarado, host de enlaces neutralizado, dominio de Reply-To y cabeceras SMTP saneadas, ≤ 2 KB por correo; ADR 0010). Nunca el asunto, el cuerpo, los adjuntos ni direcciones de correo completas. La IP puede considerarse dato personal en algunas jurisdicciones: se guarda cifrada, solo para explicar el veredicto, y se borra al desconectar el buzón.
- **Transparencia:** que el usuario vea que está conectado, qué se analiza y pueda **revocar** en cualquier momento.
- **Proporcionalidad:** es seguridad, no vigilancia. El supervisor ve alertas, no lee correos ni evalúa a las personas.
- **Sin uso secundario:** los datos no se usan para publicidad, rendimiento laboral ni disciplina.
- **Honestidad:** no prometer protección total; mostrar nivel de confianza; admitir falsos positivos/negativos.
- **Códigos de conducta de referencia:** ACM Code of Ethics, (ISC)² Code of Ethics. Útiles para citar en el pitch.

## 2. Confidencialidad y seguridad del propio sistema
Tu sistema será un objetivo valioso (acceso a bandejas de correo). Debe cumplir lo que predica.

| Riesgo | Control |
|---|---|
| Robo de tokens OAuth | Cifrar en reposo (`cryptography`/Fernet), clave fuera del repo, nunca en logs. |
| Secretos en el repositorio | `.gitignore` desde el primer commit; variables de entorno; rotar claves si se filtran. |
| Permisos excesivos | Pedir el mínimo (`gmail.readonly` + `gmail.modify` solo si usás etiquetas); explicarlos al usuario. |
| Contenido de correos expuesto | No persistir cuerpo/adjuntos; enmascarar datos personales antes de enviar a la IA; sin correos en logs. |
| Datos enviados a terceros (IA, VirusTotal, Safe Browsing) | Enviar lo mínimo; **hashes**, no archivos; leer sus términos y políticas de retención. |
| Prompt injection desde el correo | Tratar el correo como dato; salida estructurada validada; la IA no ejecuta acciones por sí sola. |
| Acceso indebido al panel | Autenticación del responsable, roles, HTTPS, registro de accesos (auditoría). |
| XSS / inyección al mostrar correos | Escapar todo; no renderizar HTML de correos. |
| Denegación por límites de API | Colas, reintentos con espera, modo degradado solo con reglas. |
| Fallos de la IA (alucinación) | Los hechos vienen de código; la IA solo redacta sobre ellos. |
| Retención | Definir cuánto se guardan las alertas y borrar al revocar o dar de baja. |

## 3. Leyes y marcos a consultar (Costa Rica y LATAM)
Verificá vigencia y alcance de cada uno:
- **Constitución Política de Costa Rica:** protección de la intimidad y de las comunicaciones privadas. Base del tema.
- **Ley de Protección de la Persona frente al tratamiento de sus datos personales (Ley 8968)** y su reglamento; la autoridad es **PRODHAB**. Revisar: consentimiento, finalidad, deber de informar, seguridad, transferencia a terceros/extranjero, registro de bases de datos.
- **Delitos informáticos en el Código Penal** (reforma por la Ley 9048): acceso indebido a sistemas o comunicaciones. Por eso **solo cuentas propias o con autorización expresa y comprobable**.
- **Normas laborales:** si el empleador monitorea el correo institucional, consultar qué exige la legislación laboral (política interna escrita, aviso previo, límites). Puede variar según contrato y sector.
- **Sectores regulados** (financiero, salud, educación, sector público): suelen tener normas propias de seguridad de la información y proveedores. Averiguar antes de ofrecerlo a esas instituciones.
- **Si hay usuarios fuera del país:** GDPR (Europa), leyes de otros países de LATAM (por ejemplo LGPD en Brasil). Aplican según dónde estén las personas.

## 4. Términos de las plataformas (suelen ser lo que bloquea en la práctica)
- **Google:** acceder a Gmail es un alcance "restringido". Para uso público exige verificación de la app y una evaluación de seguridad externa. Cumplir la **política de datos de usuario de las API de Google (uso limitado)**: no vender ni usar los datos para publicidad, no transferirlos sin base, transparencia. En modo de pruebas hay un tope de usuarios y los tokens caducan (~7 días).
- **Microsoft Graph:** requiere registro de la app y consentimiento (de usuario o de administrador). Cuentas personales (hotmail) y de organización se tratan distinto.
- **VirusTotal:** el plan gratuito tiene límites y restricciones de uso comercial; **no subas archivos privados** (se comparten con la comunidad). Usá consulta por hash.
- **Safe Browsing y otras:** revisar sus términos para uso comercial.
- **Claude API / IA:** revisar políticas de retención y uso de datos; no enviar datos personales sin enmascarar.
- **Hackathon (Dojo):** leer reglas sobre propiedad intelectual, uso de datos de terceros, código previo y demos. Preguntar al organizador si hay dudas.

## 5. Límites y cosas que NO se deben hacer
- No conectar cuentas de otras personas sin su consentimiento expreso, ni "probar con un amigo" sin avisar.
- No leer cuentas personales (el correo personal del empleado) aunque estén en el mismo dispositivo.
- No usar malware real: para adjuntos, solo el archivo de prueba **EICAR**.
- No enviar phishing de prueba a terceros; solo entre tus cuentas de prueba.
- No guardar contenido de correos "por si acaso".
- No afirmar que protege al 100 %, ni que cumple leyes que aún no verificaste.
- No usar el sistema para vigilar desempeño, productividad o conductas de las personas.

## 6. Ideas de políticas del producto (para el pitch)
- Aviso de privacidad claro y corto antes de conectar.
- Botón de revocar y de borrar datos.
- Informe de transparencia para el usuario: qué se analizó y qué alertas se generaron.
- Registro de auditoría de quién consultó qué en el panel.
- Para empresas: política interna firmada que informe del análisis automatizado del correo institucional.

## 7. Verificaciones pendientes (checklist)
- [ ] Reglas del hackathon sobre datos de terceros y APIs.
- [ ] Texto vigente de Ley 8968 y reglamento; qué exige PRODHAB para una herramienta así.
- [ ] Qué dicen las normas laborales sobre monitoreo del correo institucional.
- [ ] Requisitos de verificación de Google para el alcance de Gmail (y costos/plazos).
- [ ] Términos de VirusTotal, Safe Browsing y de la API de IA para uso comercial y retención.
- [ ] Si tu universidad tiene política sobre proyectos que tratan datos personales.
- [ ] Consultar con un profesor/mentor de ciberseguridad antes de presentar.

## 8. Limitaciones técnicas a declarar con honestidad
- Falsos positivos (correos legítimos marcados) y falsos negativos (ataques que pasan).
- Ataques nuevos o dirigidos pueden no tener señales detectables.
- Dependencia de servicios externos (disponibilidad, límites de uso).
- Hotmail/Outlook no funciona con el login de Google; requiere integración con Microsoft.
- En modo de pruebas de Google, solo funciona con usuarios de prueba registrados.

## 9. Si desarrollás desde Panamá (y el hackathon es de Costa Rica)
La ley aplicable depende de **dónde están las personas cuyos datos tratás**, de dónde opera el servicio y de
dónde estás vos. Para el hackathon (cuentas de prueba propias) el riesgo es bajo; para un producto real, no.
Consultar:
- **Panamá:** Ley 81 de 2019 de protección de datos personales y su reglamento; autoridad: **ANTAI**.
  Constitución: protección de la correspondencia y los documentos privados. Código Penal: delitos informáticos / contra medios electrónicos. Normas laborales sobre monitoreo del correo institucional.
- **Costa Rica** (si hay usuarios o datos allí): Ley 8968 y PRODHAB (ver sección 3).
- **Transferencia internacional de datos:** tu servicio, la IA y las APIs pueden estar en otros países; revisar qué exigen ambas leyes.
- **Sectores regulados en Panamá** (bancario, salud, público): normas propias de seguridad y de proveedores.
- **Contratos y premios:** como participante no residente, leé los términos del hackathon sobre propiedad intelectual y pago de premios.

> Ya aplican a Panamá las mismas reglas de ética: consentimiento, mínimo de datos y solo cuentas propias.

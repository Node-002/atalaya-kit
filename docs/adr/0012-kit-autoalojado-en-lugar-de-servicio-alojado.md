# ADR 0012 — Kit autoalojado en lugar de servicio alojado

- **Fecha:** 2026-11-21
- **Estado:** aceptada (decisión de producto tomada con la persona autora; nada de Google Cloud ni de Microsoft se ha probado).

## Contexto
Atalaya necesita leer el correo de organizaciones reales. Hay dos formas de entregarlo:
- **Servicio alojado (SaaS):** un servidor nuestro conecta los buzones de todas las organizaciones con *una* aplicación de Google.
- **Kit autoalojado:** cada organización instala su propia copia, con su propia aplicación de Google y sus propias claves.

El alcance `gmail.modify` está clasificado por Google como **restringido** ([fuente](https://developers.google.com/workspace/gmail/api/auth/scopes)). Una aplicación **externa** y pública con alcances restringidos necesita verificación (la FAQ de Google habla de unas 6 semanas, y una evaluación de seguridad si los datos se guardan o transmiten por servidores) y, sin ella, tiene un tope de 100 usuarios ([FAQ](https://support.google.com/cloud/answer/13463817), [producción](https://developers.google.com/identity/protocols/oauth2/production-readiness/overview)). No es alcanzable antes del domingo 22 de nov ni con un proyecto de una persona.

## Decisión
1. **Vender un kit autoalojado**: cada organización con Google Workspace crea su proyecto de Google Cloud, marca la aplicación como **«Interna»** (la documentación oficial indica que no requiere verificación y no tiene lista de usuarios de prueba) y corre Atalaya en su infraestructura con `docker compose`. Instrucciones: [INSTALACION.md](../INSTALACION.md).
2. **Licencia:** AGPL-3.0 más licencia comercial (ver [LICENCIA_OPCIONES.md](../LICENCIA_OPCIONES.md)). Se vende el software, las instrucciones y, opcionalmente, ayuda de instalación; **no** se aloja ni se ve ningún dato de la organización.
3. **La demo pública no cambia:** sigue siendo solo modo demo (ADR 0004). El `Dockerfile` pasa a tres etapas (`base`, `kit`, `demo`) con `demo` como **última** etapa, de modo que `docker build .` y Render siguen construyendo lo mismo. La etapa `kit` no fuerza el modo demo; arranca en `gmail` y se niega a arrancar si faltan variables obligatorias (`app/kit_preflight.py`).
4. La URI de redirección de Google se deriva de `ATALAYA_BASE_URL` (puede fijarse con `GOOGLE_REDIRECT_URI`).

## Por qué (razonamiento)
- **Verificación de Google:** el kit la evita porque cada organización es dueña de su aplicación interna; nosotros no tenemos que verificar nada. (⚠️ Que una app interna quede exenta de la evaluación de seguridad para alcances restringidos no se confirmó en el texto completo de las páginas oficiales leídas.)
- **Custodia de tokens:** en un SaaS custodiaríamos los tokens de lectura y etiquetado de los buzones de *todos* los clientes: un único punto de ataque, y una brecha nuestra sería una brecha de todos. Con el kit, los tokens están cifrados en el servidor de cada organización con una clave que nosotros no vemos.
- **Responsabilidad y cumplimiento:** con el kit, la organización es la responsable del tratamiento de sus datos; dependemos menos de una política de privacidad aún sin revisión legal ([POLITICA_PRIVACIDAD.md](../POLITICA_PRIVACIDAD.md)).
- **Encaja con el diseño:** «no guardar cuerpos», tokens cifrados con Fernet y cuarentena reversible ya asumen una instalación controlada por la organización.

## Alternativas descartadas
| Alternativa | Por qué no ahora |
|---|---|
| Servicio alojado con una app externa de Google | Requiere verificación y evaluación de seguridad (semanas, posible costo); tope de 100 usuarios mientras tanto |
| Servicio alojado con una app «interna» nuestra | Una app interna solo sirve a cuentas de la organización dueña del proyecto: no sirve a clientes |
| Reducir el alcance (`gmail.readonly`) | También es restringido y perderíamos etiquetar/mover; no elimina el problema de verificación |
| Delegación en todo el dominio (cuenta de servicio) | Da acceso a *todos* los buzones sin consentimiento individual; más riesgo y requiere un administrador; no se evaluó a fondo |
| Motor de análisis como API para otros desarrolladores | Otra línea de negocio; ver [NEGOCIO_Y_PROBLEMA.md](../NEGOCIO_Y_PROBLEMA.md) |

## Hoja de ruta
1. **Kit Gmail/Workspace** (esta decisión; hecho en el repositorio, **sin probar con una organización real**).
2. **Kit Microsoft 365**, mediante el proveedor `MailProvider` (ADR 0001). **No implementado.** Diseño:
   - Un nuevo `MicrosoftGraphProvider` que cumpla la misma interfaz que `GmailProvider` (listar mensajes nuevos de la bandeja de entrada, etiquetar y mover a una carpeta de cuarentena; nunca borrar ni enviar).
   - Cada organización crea un **registro de aplicación de un solo inquilino** («Single tenant only») en su propio Microsoft Entra ID, y su administración **da el consentimiento** en su inquilino. Microsoft recomienda «un solo inquilino» para la mayoría de las aplicaciones, de uso solo para usuarios de ese inquilino ([registro de aplicaciones](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app)); el consentimiento de administrador se concede en el portal y Microsoft lo describe como operación sensible ([consentimiento de administrador](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/grant-admin-consent)).
   - **Permisos probables de Microsoft Graph:** `Mail.ReadWrite` (las páginas de mover y actualizar mensaje lo listan como el permiso de menor privilegio, delegado y de aplicación: [mover](https://learn.microsoft.com/en-us/graph/api/message-move), [actualizar categorías](https://learn.microsoft.com/en-us/graph/api/message-update)). «Mover» crea una copia en la carpeta destino y elimina el original, así que el id puede cambiar. Las categorías de Outlook harían de «etiqueta». Si se usan permisos de **aplicación** (sin persona conectada), se restringe el acceso a buzones concretos con *RBAC for Applications* de Exchange Online ([documentación](https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac)); hay que quitar el permiso sin restricción en Entra o el límite no surte efecto. Alternativa: permisos **delegados** con invitación por buzón, como en Gmail. ⚠️ Los nombres y requisitos de consentimiento exactos de `Mail.Read*` **no se pudieron leer** en la página de referencia de permisos; hay que confirmarlos.
   - **Por qué no requeriría verificación de editor:** según Microsoft, la verificación de editor es «principalmente para desarrolladores que crean aplicaciones multiinquilino» ([visión general](https://learn.microsoft.com/en-us/entra/identity-platform/publisher-verification-overview)); con un registro de un solo inquilino dentro del propio inquilino de la organización no hay consentimiento entre inquilinos. ⚠️ La página **no dice explícitamente** que una app de un solo inquilino esté exenta; es una inferencia que hay que confirmar con un inquilino real.
   - Esfuerzo: un proveedor, flujo OAuth (MSAL), pruebas con respuestas simuladas y una guía de instalación paralela. Sin estimar.
3. **Servicio alojado** cuando Google verifique la aplicación (y exista capacidad para custodiar datos): requiere verificación de alcance restringido, evaluación de seguridad, política de privacidad revisada por una persona abogada y una operación real (copias de seguridad, soporte, respuesta a incidentes).

## Consecuencias
- No hay un único «enlace al producto» para clientes: hay una instalación por organización. El soporte es más difícil (no vemos sus registros) y la barrera de entrada es una persona de TI con Workspace.
- La persona instaladora debe operar Docker, HTTPS, respaldos y actualizaciones. Se reduce con la guía y `tools/kit/verificar_instalacion.py`.
- El Marketplace publica una ficha y un paquete, no una aplicación en ejecución ([MARKETPLACE_FICHA.md](../MARKETPLACE_FICHA.md)).
- Todo lo de Google Cloud/Workspace está **sin verificar con una organización real**; el CI prueba la imagen y el compose con datos falsos al subir.

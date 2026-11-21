# Contrato de licencia comercial de Atalaya (kit autoalojado) — BORRADOR

> **Estado: borrador de trabajo. No lo revisó una persona abogada y no es asesoría legal.** Está escrito para que una persona abogada de la jurisdicción correspondiente lo revise, lo corrija y lo complete **antes de usarlo con un cliente real**. Todo lo que aparece entre corchetes `[POR DEFINIR]` es una decisión pendiente, no un dato.
>
> **Base y atribución:** esta estructura y varias ideas parten del acuerdo estándar *Software License Agreement* (versión 1.1) de **Common Paper**, publicado bajo la licencia **Creative Commons Atribución 4.0 Internacional (CC BY 4.0)**: <https://commonpaper.com/standards/software-license-agreement/> · <https://creativecommons.org/licenses/by/4.0/>. **Se hicieron cambios:** se tradujo y se redactó de nuevo para el kit autoalojado de Atalaya, se añadieron cláusulas sobre doble licencia (AGPL-3.0), vigilancia de buzones de personas empleadas, uso opcional de IA de terceros y soporte, y se eliminaron partes pensadas para el derecho estadounidense. Common Paper no respalda este texto. La revisión de Common Paper la hicieron personas abogadas; **esta adaptación no**.
>
> Fecha del borrador: 21 de noviembre de 2026. Producto: Atalaya (kit autoalojado). Relación con los demás documentos: [LICENCIA_OPCIONES.md](LICENCIA_OPCIONES.md), [MARKETPLACE_FICHA.md](MARKETPLACE_FICHA.md), [INSTALACION.md](INSTALACION.md), [POLITICA_PRIVACIDAD.md](POLITICA_PRIVACIDAD.md), [TERMINOS_DE_USO.md](TERMINOS_DE_USO.md), [adr/0012-kit-autoalojado-en-lugar-de-servicio-alojado.md](adr/0012-kit-autoalojado-en-lugar-de-servicio-alojado.md).

## 0. Cómo leer este borrador
Un acuerdo de este tipo tiene dos partes que se rellenan por cliente y unos términos fijos:
1. **Portada (Hoja de pedido y Términos clave):** lo comercial y lo que cambia de un cliente a otro.
2. **Términos estándar:** el texto que se queda igual.
3. **Anexos:** descripción del software y lista de preguntas para la persona abogada.

**Orden de prelación:** si la Portada contradice los Términos estándar, **manda la Portada**.

### Decisiones que solo puedes tomar tú (antes de dárselo a la abogada)
| # | Decisión | Opciones | Mi sugerencia (no vinculante) |
|---|---|---|---|
| 1 | ¿Quién es **«Proveedor»**? | Tú como persona, o una sociedad que constituyas | Preguntar a la abogada: una sociedad separa tu responsabilidad personal |
| 2 | **Precio** y forma de cobro | Por organización/año, por buzón/año, pago único | Sin definir hasta medir el costo de IA y validar con clientes |
| 3 | **Plazo** | 12 meses con renovación, o perpetuo con soporte anual | Un año con renovación; menos riesgo |
| 4 | **Tope de responsabilidad** | 1× lo pagado en los últimos 12 meses, o un monto fijo | Alguno bajo; es la protección más importante |
| 5 | **Soporte** | Ninguno, correo en horario hábil, o de pago | «Mejor esfuerzo», sin acuerdo de nivel de servicio |
| 6 | **Ley aplicable y foro** | País, tribunales o arbitraje | Lo decide la abogada (ver Anexo 2) |
| 7 | **IA de terceros** | Apagada por defecto (así está hoy), el cliente la activa bajo su cuenta | Mantenerlo así |

---

# PARTE A — PORTADA

## A.1 Hoja de pedido (Order Form)
| Campo | Valor |
|---|---|
| **Proveedor** | `[nombre completo o razón social]` · `[identificación fiscal]` · `[dirección]` · `[correo de notificaciones]` |
| **Cliente** | `[razón social de la organización]` · `[identificación fiscal]` · `[dirección]` · `[persona de contacto y correo]` |
| **Fecha de entrada en vigor** | `[fecha de la última firma]` |
| **Software** | Atalaya, kit autoalojado, versión `[x.y.z]` y sus actualizaciones durante la vigencia. Descripción en el Anexo 1 |
| **Documentación** | Guía de instalación (`docs/INSTALACION.md` o `INSTALLATION.en.md`) y documentos enlazados desde ella |
| **Prueba piloto** (opcional) | `[sí/no]` · duración `[días]` · tarifa `[gratis / monto]` · cambios durante la prueba: `[por ejemplo, sin garantía ni indemnización, tope de responsabilidad reducido]` |
| **Periodo de suscripción** | `[12 meses]` desde la fecha de entrada en vigor |
| **Tarifa** | `[monto y moneda]` por `[organización / buzón]` por `[año]`. Impuestos: `[incluidos / no incluidos]` |
| **Aumento en la renovación** | `[0 % / hasta __ %]` con aviso de `[__]` días |
| **Forma de pago** | `[factura a __ días / transferencia / otra]` |
| **Renovación automática** | `[sí/no]` · aviso de no renovación: `[30]` días antes del vencimiento |
| **Usos permitidos** | Uso **interno** del Cliente para vigilar los buzones de su propia organización. `[Opcional: sociedades filiales listadas]` |
| **Límites de la licencia** | Hasta `[N]` buzones vigilados · `[una / N]` instalaciones · sin transferir a otra organización |
| **Periodo de garantía** | `[30]` días desde la entrega de cada versión |
| **Procedimiento de eliminación al terminar** | El Cliente desinstala el software, borra los volúmenes de datos y la clave de cifrado, revoca el acceso de la aplicación en su cuenta de Google y lo confirma por escrito |
| **Auditoría de cumplimiento** | `[sí/no]` · aviso previo de `[__]` días, máximo `[una]` vez al año, solo del número de buzones y de instalaciones |
| **Servicios incluidos** | `[Actualizaciones de la versión durante la suscripción]` · Soporte: `[ninguno / correo en horario hábil, respuesta en __ días hábiles, sin nivel de servicio garantizado]` |
| **Cambios específicos a este pedido** | `[ninguno]` |
| **Firmas** | Proveedor: `[nombre, cargo, fecha]` · Cliente: `[nombre, cargo, fecha]` |

## A.2 Términos clave
| Campo | Valor |
|---|---|
| **Ley aplicable** | `[país o jurisdicción: POR DEFINIR con la persona abogada]` |
| **Foro** | `[tribunales de __ / arbitraje en __ según el reglamento de __ / POR DEFINIR]` |
| **Tope general de responsabilidad** | `[una vez / __ veces]` las tarifas pagadas por el Cliente en los 12 meses anteriores a la reclamación `[o un monto fijo de __]` |
| **Reclamaciones con tope incrementado** | `[incumplimiento de confidencialidad, excluyendo brechas de datos y seguridad]` · tope incrementado: `[__ veces las tarifas de 12 meses / monto fijo]` |
| **Reclamaciones sin tope** | Lo que la ley no permita limitar, y `[indemnización del Cliente por los usos prohibidos de la cláusula 2.3]` |
| **Reclamaciones cubiertas por el Proveedor (indemnización)** | Infracción de propiedad intelectual de terceros por el software tal como se entrega |
| **Reclamaciones cubiertas por el Cliente** | `[Uso del software para vigilar buzones sin base legal o sin informar a las personas afectadas; incumplimiento de la cláusula 2]` |
| **Garantías adicionales** | `[ninguna]` |
| **Acuerdo de tratamiento de datos (DPA)** | `[No aplica: el Proveedor no accede ni trata los datos del Cliente (cláusula 10). Si el Proveedor presta soporte con acceso a datos, se firmará un DPA aparte.]` |
| **Cambios a los Términos estándar** | `[ninguno]` |

---

# PARTE B — TÉRMINOS ESTÁNDAR

## 1. Software y licencia
**1.1 Concesión.** Durante el Periodo de suscripción, el Proveedor concede al Cliente una licencia **limitada, no exclusiva, no sublicenciable e intransferible** para instalar, ejecutar y usar el Software, en su propia infraestructura, para los Usos permitidos y dentro de los Límites de la licencia de la Hoja de pedido.

**1.2 Relación con la licencia AGPL-3.0 (doble licencia).** El código de Atalaya está publicado bajo la **GNU Affero General Public License v3.0 (AGPL-3.0)**. El Proveedor es titular de los derechos y ofrece además esta **licencia comercial**. Entre ambas:
- **Mientras esté vigente este acuerdo, el Cliente puede usar el Software bajo estos términos y no está obligado a las condiciones de la AGPL-3.0 que este acuerdo reemplace** (por ejemplo, publicar sus modificaciones o integrarlo en un producto cerrado), **dentro del alcance de los Usos permitidos**.
- **Si este acuerdo termina o el Cliente se excede de los Usos permitidos, solo quedan los derechos que da la AGPL-3.0.**
- El Software incluye componentes de terceros con sus propias licencias (ver `NOTICE`); esta licencia no cambia esas licencias.
`[La persona abogada debe confirmar que el Proveedor tiene todos los derechos necesarios para licenciar el Software bajo ambas licencias, incluido el código de terceras personas si algún día se aceptan contribuciones.]`

**1.3 Cuentas y personas usuarias.** El Cliente es responsable de quien administra Atalaya y de cada acción que se haga con las credenciales de su instalación.

**1.4 Comentarios.** Si el Cliente envía sugerencias, el Proveedor puede usarlas libremente sin obligación de pago ni atribución.

**1.5 Sin datos de uso hacia el Proveedor.** El Software **no envía telemetría ni datos de uso** al Proveedor. Si el Cliente decide compartir información (por ejemplo, para pedir soporte), lo hace voluntariamente.

**1.6 Actualizaciones.** Durante el Periodo de suscripción el Cliente puede recibir las versiones nuevas sin costo adicional. El Cliente es responsable de instalarlas; el Proveedor no actualiza instalaciones ajenas.

**1.7 Reserva de derechos.** El Proveedor conserva todos los derechos sobre el Software, la marca «Atalaya» y la documentación. No se transfiere ninguna propiedad.

## 2. Restricciones y obligaciones del Cliente
**2.1 Restricciones.** El Cliente no puede, salvo lo permitido por la AGPL-3.0 o por la ley que no se pueda excluir: (a) sublicenciar, vender, alquilar o ceder el Software; (b) ofrecer el Software como **servicio a terceras organizaciones**; (c) eliminar avisos de derechos o de licencia; (d) usarlo para competir ofreciendo un producto equivalente basado en este código; (e) eludir los límites de la licencia (por ejemplo, el número de buzones); (f) usarlo en infracción de leyes o sanciones aplicables.

**2.2 Vigilancia de buzones de personas empleadas o usuarias.** Atalaya analiza correos de personas. El Cliente es el **único responsable** de que esa vigilancia tenga una **base legal**, de **informar** a las personas afectadas y obtener su **consentimiento** cuando la ley lo exija, de cumplir las leyes laborales y de protección de datos que le apliquen, y de usar la pantalla de consentimiento del Software o una equivalente. El Proveedor no revisa ni garantiza ese cumplimiento.

**2.3 Usos prohibidos.** Está prohibido usar el Software para vigilar buzones sin la autorización de la persona titular o de la organización que los administra, para acosar, discriminar o espiar, o para cualquier fin ilegal.

**2.4 Infraestructura, claves y seguridad.** El Cliente es responsable de: su servidor y su red; crear y administrar su propia aplicación de Google (o del proveedor de correo que use) y sus credenciales; **proteger y respaldar la clave de cifrado** (sin ella, los datos guardados son ilegibles y el Proveedor no puede recuperarlos); mantener HTTPS, el reloj del servidor y las actualizaciones; limitar quién administra; y revocar accesos al terminar.

**2.5 Suspensión.** El Proveedor puede dejar de ofrecer actualizaciones o soporte si hay incumplimiento de las cláusulas 2.1 a 2.3 o impago superior a `[30]` días de una cantidad no disputada de buena fe. El Proveedor **no puede apagar** una instalación del Cliente: el Software corre en su infraestructura.

## 3. Pagos e impuestos
**3.1 Tarifas.** El Cliente paga la Tarifa de la Hoja de pedido, en `[moneda]`. Salvo que se indique otra cosa, las tarifas **no son reembolsables**, excepto lo que prevea esta cláusula `[y la cláusula 4.4]`.
**3.2 Facturación y pago.** Según la Hoja de pedido. `[Cargo automático solo con autorización expresa del Cliente.]`
**3.3 Impuestos.** `[POR DEFINIR por la persona abogada y contadora: quién paga los impuestos indirectos, retenciones y cargos bancarios, y cómo se factura desde la jurisdicción del Proveedor al Cliente.]`
**3.4 Disputas.** El Cliente debe avisar de una disputa de buena fe **antes del vencimiento** y pagar lo no disputado; las partes intentarán resolverlo en `[15]` días.

## 4. Plazo y terminación
**4.1 Vigencia y renovación.** El pedido empieza en la fecha de entrada en vigor y dura el Periodo de suscripción. `[Se renueva por periodos iguales salvo aviso de no renovación con el preaviso indicado.]`
**4.2 Terminación por incumplimiento.** Cualquiera de las partes puede terminar si la otra incumple materialmente y no lo subsana en `[30]` días desde el aviso, o de inmediato si el incumplimiento no es subsanable.
**4.3 Insolvencia.** Cualquiera puede terminar si la otra cesa su actividad, se declara insolvente o entra en concurso o liquidación.
**4.4 Fuerza mayor.** Ninguna parte responde por incumplimientos causados por hechos fuera de su control razonable; si impiden el cumplimiento por `[30]` días consecutivos o más, cualquiera puede terminar y el Proveedor devuelve lo prepagado por el periodo no usado.
**4.5 Efectos.** Al terminar: el Cliente deja de usar el Software, aplica el Procedimiento de eliminación y devuelve o destruye la información confidencial del Proveedor; el Proveedor emite la factura final. Si el Cliente quiere seguir usando el Software después, solo podrá hacerlo bajo la **AGPL-3.0** y sus condiciones.
**4.6 Supervivencia.** Siguen vigentes las cláusulas que por su naturaleza deban hacerlo (1.2 último párrafo, 1.7, 2.2 a 2.4, 3 hasta el pago, 5 a 9, 11 y 12).

## 5. Garantías
**5.1 Mutuas.** Cada parte declara que tiene poder y capacidad para firmar y cumplir este acuerdo y que cumplirá las leyes que le apliquen.
**5.2 Garantía del Proveedor.** Durante el Periodo de garantía, el Software, tal como se entrega y usado según la Documentación, funcionará **sustancialmente** como la Documentación lo describe.
**5.3 Exclusiones.** No hay garantía si el Cliente modificó el Software, lo usó fuera de lo permitido, no instaló una actualización que corregía el problema, o el fallo viene de su infraestructura, de Google u otro proveedor, o de una clave o configuración errónea.
**5.4 Remedio exclusivo.** Si el Software incumple la garantía, el Proveedor lo corregirá o lo reemplazará dentro de un plazo razonable; si no puede, el Cliente puede terminar el pedido y recibir el reembolso proporcional de lo pagado por el periodo restante. **Ese es el único remedio por incumplimiento de la garantía.**

## 6. Exclusión de garantías
Salvo lo dicho en la cláusula 5, el Software se entrega **«tal cual»** y **«según disponibilidad»**. El Proveedor **no garantiza** que el Software funcione sin errores ni interrupciones, **ni que detecte todos los ataques, ni que no genere falsas alarmas**: Atalaya es una herramienta de apoyo y **la decisión final es siempre de una persona**. Se excluyen, en la medida en que la ley lo permita, las garantías implícitas de comerciabilidad, idoneidad para un fin particular, titularidad y no infracción. `[La persona abogada debe verificar qué exclusiones permite la ley aplicable a este tipo de cliente.]`

## 7. Limitación de responsabilidad
**7.1 Tope.** La responsabilidad total de cada parte frente a la otra por todas las reclamaciones derivadas de este acuerdo **no excede el Tope general**. Las Reclamaciones con tope incrementado se rigen por el Tope incrementado.
**7.2 Daños excluidos.** Ninguna parte responde por **daños indirectos, consecuentes, especiales o punitivos, ni por lucro cesante, pérdida de ingresos, de clientela, de datos o de oportunidades de negocio**, aunque se le haya avisado de la posibilidad, incluidos los daños por **una amenaza no detectada o por un correo legítimo aislado por error**.
**7.3 Alcance.** Estos límites valen para cualquier teoría de responsabilidad (contractual, extracontractual u otra).
**7.4 Excepciones.** El Tope y la exclusión de daños no aplican a las Reclamaciones sin tope. La exclusión de daños no aplica a las Reclamaciones con tope incrementado ni al incumplimiento de la licencia por parte del Cliente. Nada limita la responsabilidad que **la ley no permita limitar** (por ejemplo, dolo o negligencia grave, según la ley aplicable).

## 8. Indemnización
**8.1 Del Proveedor.** El Proveedor defenderá y mantendrá indemne al Cliente frente a reclamaciones de terceros que aleguen que el Software, **tal como se entrega y usado según este acuerdo**, infringe sus derechos de propiedad intelectual.
**8.2 Del Cliente.** El Cliente defenderá y mantendrá indemne al Proveedor frente a las Reclamaciones cubiertas por el Cliente (cláusula A.2).
**8.3 Procedimiento.** La parte que reclama avisa sin demora, permite al indemnizante dirigir la defensa y colabora a costa de este; el indemnizante no puede aceptar un acuerdo que admita culpa de la otra parte sin su consentimiento.
**8.4 Cambios.** Si hay una reclamación de propiedad intelectual, el Proveedor puede obtener el derecho de uso, modificar el componente, o terminar el pedido y devolver lo prepagado del periodo restante.
**8.5 Exclusiones.** No hay indemnización si la reclamación viene de modificaciones del Cliente, de una combinación con productos de terceros, de no instalar una actualización, o de uso fuera de lo permitido.
**8.6 Remedio exclusivo.** Esta cláusula establece la responsabilidad total del indemnizante por esas reclamaciones.

## 9. Confidencialidad
Cada parte protegerá la información confidencial de la otra con el mismo cuidado que usa para la suya (y nunca menos que uno razonable), la usará solo para ejecutar este acuerdo y no la revelará salvo a personas que la necesiten y estén obligadas a reservarla, o por exigencia legal (avisando antes si es posible). No es confidencial lo que ya sea público sin culpa de quien lo recibe, lo conocido legítimamente, o lo desarrollado de forma independiente. **El código fuente de Atalaya es público bajo la AGPL-3.0 y no es confidencial.** Los datos de los buzones del Cliente son confidenciales del Cliente y el Proveedor no los recibe.

## 10. Datos y privacidad
**10.1 Alojamiento por el Cliente.** Los datos que Atalaya procesa (veredictos, señales, metadatos técnicos de cabeceras y, si se activa la IA, el texto enviado al proveedor de IA) **residen y se procesan en la infraestructura del Cliente**. El Proveedor **no accede** a ellos, no los copia y no es su encargado de tratamiento salvo que el Cliente le dé acceso expreso para soporte (en ese caso, solo mientras dure el soporte y bajo el DPA que se firme).
**10.2 Qué guarda el Software.** Según el [consentimiento del Software](../app/static/invite.html) y la [política de privacidad](POLITICA_PRIVACIDAD.md): veredicto, señales, identificador, estado y una lista limitada de metadatos técnicos de cabeceras; **nunca** asunto, cuerpo ni adjuntos. El Cliente debe ajustar sus propios avisos a su realidad.
**10.3 IA de terceros (opcional).** La explicación con IA está **apagada por defecto**. Si el Cliente la activa con su propia clave, para los correos sospechosos se envía a ese proveedor (hoy Anthropic) un texto con teléfonos, cuentas y cédulas enmascarados. **El Cliente contrata y se relaciona directamente con ese proveedor**, es responsable de sus costos y de sus condiciones de privacidad, y debe informarlo a las personas afectadas. El Proveedor de Atalaya no es parte de esa relación.
**10.4 Incidentes.** El Cliente decide cómo gestionar y notificar los incidentes en su infraestructura. El Proveedor avisará de las vulnerabilidades del Software que conozca y publicará correcciones.

## 11. Soporte y actualizaciones
Solo lo que diga la Hoja de pedido. Salvo que se pacte otra cosa: soporte de **mejor esfuerzo**, sin acuerdo de nivel de servicio, sin garantía de tiempos de respuesta ni de disponibilidad, y en el idioma `[español / inglés]`. Las correcciones de seguridad se publican en el repositorio; instalarlas es responsabilidad del Cliente.

## 12. Disposiciones generales
**12.1 Acuerdo completo.** Este acuerdo (Portada, Términos estándar y Anexos) reemplaza cualquier acuerdo previo sobre el mismo objeto. Solo se modifica por escrito firmado por ambas partes.
**12.2 Ley aplicable y foro.** Los de la Portada. `[POR DEFINIR]`
**12.3 Medidas urgentes.** Cualquiera puede pedir medidas cautelares a un tribunal competente para proteger su propiedad intelectual o su información confidencial.
**12.4 Cesión.** Ninguna parte puede ceder este acuerdo sin el consentimiento escrito de la otra, salvo en una fusión o venta de la totalidad del negocio relacionado, avisando por escrito.
**12.5 Notificaciones.** Por escrito a las direcciones de la Hoja de pedido; los avisos por correo electrónico valen cuando se confirme su recepción. `[Confirmar validez según la ley aplicable.]`
**12.6 Independencia de las partes.** No hay sociedad, mandato ni relación laboral entre ellas.
**12.7 Nulidad parcial.** Si una cláusula es inválida, el resto sigue vigente y se interpreta la inválida de la forma más cercana a su intención.
**12.8 Cumplimiento.** Exportación, sanciones y anticorrupción: cada parte cumplirá las leyes que le apliquen. `[La persona abogada debe decidir qué referencias normativas incluir; el texto original estadounidense se omitió.]`
**12.9 Firma electrónica y copias.** Puede firmarse electrónicamente y en copias. `[Confirmar validez de la firma electrónica en la jurisdicción.]`
**12.10 Idioma.** Si hay versiones en otro idioma, prevalece `[el español]`.

## 13. Definiciones
**Documentación:** las guías y la documentación técnica del Software indicadas en la Hoja de pedido. **Software:** Atalaya, kit autoalojado, con sus actualizaciones durante el Periodo de suscripción. **Usos permitidos:** los de la Hoja de pedido. **Información confidencial:** la que una parte revele a la otra y esté marcada como confidencial o sea razonablemente confidencial por su naturaleza. **Periodo de suscripción:** el de la Hoja de pedido. **Reclamaciones con tope incrementado / sin tope / cubiertas:** las de los Términos clave.

---

# ANEXOS

## Anexo 1 — Descripción del Software
Atalaya es un agente que revisa los correos de los buzones conectados de una organización, calcula el riesgo con reglas verificables (autenticación SPF/DKIM/DMARC, dominios parecidos, enlaces y otras señales), explica el motivo en español y, **solo con la aprobación de una persona**, aísla el correo de la bandeja de forma reversible. No borra ni envía correos. Incluye un panel con rol de administración y de supervisión de solo lectura, informes en PDF y registro de decisiones con motivo. Versión del kit: `[x.y.z]`. Requisitos y límites: ver [INSTALACION.md](INSTALACION.md) y [MARKETPLACE_FICHA.md](MARKETPLACE_FICHA.md) (hoy: Gmail y Google Workspace; Microsoft 365 en la hoja de ruta; sin adjuntos ni reputación de enlaces).

## Anexo 2 — Preguntas y puntos para la persona abogada
1. **Titularidad y capacidad de licenciar:** ¿el titular tiene todos los derechos para ofrecer la doble licencia AGPL-3.0 y comercial? ¿Qué pasa con las dependencias de terceros y con el código generado con herramientas de IA? ¿Conviene registrar la marca «Atalaya» y el software?
2. **Quién firma como Proveedor:** persona natural o sociedad; efectos sobre la responsabilidad personal; impuestos y cobro desde Panamá.
3. **Ley aplicable y foro:** qué opción es práctica para clientes de varios países (litigio, arbitraje, mediación); validez de las cláusulas de limitación de responsabilidad y de exclusión de garantías frente a clientes de cada país.
4. **Protección de datos personales:** ¿qué obligaciones tiene el Cliente al vigilar buzones de personas empleadas (base legal, aviso, consentimiento, derechos de las personas)? ¿Qué obligaciones, si alguna, tendría el Proveedor aunque no acceda a los datos? ¿Hace falta un DPA o cláusulas de transferencia por el uso opcional de IA de terceros?
5. **Derecho laboral:** límites a la vigilancia de correo corporativo; texto recomendado para los avisos a personas empleadas.
6. **Cláusula de doble licencia (1.2):** ¿es clara y exigible? ¿Cómo se evita que el Cliente use el software bajo la licencia comercial y después lo reutilice sin pagar?
7. **Soporte y responsabilidad por seguridad:** cómo acotar lo que se promete (soporte, correcciones de vulnerabilidades, notificación de fallos) sin asumir un nivel de servicio.
8. **Venta en el Marketplace de Dojo:** qué licencia o permisos concede el Proveedor a Dojo, y si las condiciones de la plataforma son compatibles con este acuerdo. (Pregunta aún sin respuesta de los organizadores; ver [PREGUNTAS_ORGANIZADORES.md](PREGUNTAS_ORGANIZADORES.md).)
9. **Términos de uso y política de privacidad** del sitio y de la demo pública: revisarlos o reemplazarlos (borradores en este repositorio).
10. **Firma electrónica, facturación e impuestos** del tipo de operación (licencia de software transfronteriza).

## Anexo 3 — Aviso de licencia del texto base
Partes de este documento derivan del *Software License Agreement* v1.1 de Common Paper, con licencia CC BY 4.0. Atribución: «Common Paper Software License Agreement (Version 1.1) — © Common Paper, publicado bajo CC BY 4.0». Este documento es una obra derivada, **modificada y traducida**; los cambios principales están descritos al comienzo. La licencia con la que se publique esta adaptación la decide la persona titular, conservando siempre la atribución a Common Paper.

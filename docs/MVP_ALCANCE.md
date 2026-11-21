# Alcance del MVP — Atalaya (congelado el 9 nov 2026)

> Regla: lo que no está en "Entra" no se construye, salvo que sobre tiempo después de cumplir la definición de terminado.
> Trabajo en solitario, ~3 días. Meta de entrega: **domingo 22, antes de las 10:00 p. m. (Panamá)**.

## Recorrido único (vertical slice)
```
Login Google → leer correo nuevo → analizar → decidir riesgo → actuar (etiqueta)
→ alerta en panel → persona aprueba o rechaza → registro de auditoría
```
Primero se hace **todo el recorrido con lo mínimo**; después se mejora cada pieza.

## Entra (obligatorio)
| # | Pieza | Detalle |
|---|---|---|
| 1 | Login con Google | Usuarios de prueba, texto de consentimiento claro, botón de desconectar |
| 2 | Lectura de correos nuevos | Consulta cada minuto con la API de Gmail |
| 3 | Análisis por reglas | SPF/DKIM/DMARC (cabecera de autenticación), dominio parecido a marcas (lista CR + Panamá), remitente vs. dirección de respuesta, enlaces acortados, lenguaje de urgencia |
| 4 | Explicación con IA | Salida JSON validada; el correo se trata como dato hostil; datos personales enmascarados |
| 5 | Motor de decisión | Bajo: nada. Medio: etiqueta "Revisar". Alto: etiqueta "Sospechoso" y pide aprobación para cuarentena |
| 6 | Acción en Gmail | Aplicar etiquetas; cuarentena = quitar de la bandeja + etiqueta (reversible, nunca borrar) |
| 7 | Panel de alertas | Lista de alertas con señales y explicación; botones Aprobar / Rechazar / "Es legítimo" |
| 8 | Estado de cobertura básico | Conectada / desconectada (detectar token revocado) con alerta |
| 9 | Registro de auditoría | Quién aprobó qué y cuándo |
| 10 | Privacidad | Solo se guarda veredicto, señales e ID; tokens cifrados; sin cuerpo ni adjuntos |
| 11 | **Modo demo público sin Google** | Dojo pide una "Live app" que los jueces puedan abrir y probar. Con Gmail en modo de pruebas, solo los usuarios de prueba registrados pueden iniciar sesión, así que los jueces no podrían entrar. El modo demo trae una bandeja simulada (phishing, legítimo, inyección) y permite recorrer el flujo completo sin conectar ninguna cuenta real |

## Extras (solo si se cumple la definición de terminado)
En este orden: 1) Safe Browsing para enlaces, 2) hash de adjuntos (VirusTotal) con archivo EICAR,
3) alertas por Telegram con botones Aprobar/Rechazar, 4) mini lección por amenaza, 5) panel de cobertura ampliado.

## No entra
- Conector de Microsoft (Microsoft 365 / Outlook) **completo**: se diseña la interfaz común para soportarlo y se implementa solo si el conector de Gmail ya funciona de punta a punta (meta: sábado al mediodía, hora de Panamá). Si no, queda como siguiente paso en el pitch.
- Análisis de correo saliente o prevención de fuga de datos (DLP).
- Borrar o enviar correos desde el sistema.
- Varias organizaciones, facturación, roles complejos.
- Verificación de Google para uso público.
- Captura de pantalla / OCR.

## Definición de terminado (para la demo)
1. Un phishing simulado llega y aparece como **Sospechoso** en Gmail y en el panel, con señales y explicación.
2. Un correo legítimo pasa sin alarma.
3. Un correo con instrucción oculta para la IA ("ignora lo anterior…") **sigue detectándose**.
4. La persona aprueba la cuarentena desde el panel y el correo sale de la bandeja.
5. Al revocar el acceso desde la cuenta de prueba, el panel muestra la cuenta como **sin cobertura**.
6. Resultado medible: detección sobre ~30 correos de prueba (aciertos, falsos positivos).
7. Desplegado, con enlace público y video de respaldo.

## Presupuesto de tiempo y cortes
| Bloque | Meta | Corte |
|---|---|---|
| Vie 20 (desde las 10:00, Panamá) | Login + lectura + reglas básicas | Si OAuth no funciona en ~4 h → **Plan B**: entrada manual del correo |
| Sáb 21 | IA, decisión, etiquetas, panel, aprobación | Si se atrasa, recortar auditoría o cobertura (no el flujo principal) |
| Dom 22 hasta el mediodía | Pruebas, seguridad (plugins), despliegue | **Congelar funciones al mediodía** |
| Dom 22 tarde | Video, descripción, entrega | Entregar antes de las 10:00 p. m. (Panamá) |

## Estructura sugerida de `app/`
```
app/
├── main.py          # FastAPI y rutas
├── auth.py          # OAuth y tokens cifrados
├── gmail.py         # lectura y etiquetas
├── analyzers/       # reglas: autenticación, dominios, enlaces, urgencia
├── llm.py           # explicación y defensa contra prompt injection
├── decision.py      # niveles de riesgo y acciones
├── store.py         # SQLite: veredictos, estados, auditoría
├── static/          # panel HTML/JS
└── tests/           # correos de prueba y pruebas
```

## Preparación antes del 20 (sin escribir el producto)
- [ ] Correos de prueba (30) en `docs/` o en una carpeta fuera del repositorio.
- [ ] Lista de marcas a vigilar: Costa Rica y Panamá (verificar nombres reales).
- [ ] Cuentas Gmail de prueba propias y proyecto de Google Cloud en modo de pruebas (registrar en `ESTADO_INICIAL.md`).
- [ ] 2–3 conversaciones con personas de TI.

## Nota (17 nov): publicación en el Marketplace de Dojo
Al entregar ("Submit and publish"), Dojo lista el proyecto **gratis y públicamente** en su Marketplace, bajo el nombre del equipo, y el capitán es quien lo opera. Consecuencias para Atalaya:
- La app pública debe funcionar **solo en modo demo** (bandeja simulada). No ofrecer conexión de cuentas reales de Gmail al público: Gmail está en modo de pruebas (solo usuarios registrados) y no hay verificación de Google ni evaluación legal de protección de datos.
- Mostrar un aviso claro en la app: "Demostración con datos simulados. No conectes tu correo real."
- Verificar en `View Project` que el track siga siendo **AI Operators**, aunque el Marketplace muestre la etiqueta "Tool".
- Antes de entregar: repositorio sin claves, enlaces probados en ventana privada y aviso de privacidad visible.

## Cambio de alcance (20 nov, tarde): varios buzones e invitaciones
Decidido por la persona autora. En una empresa, quien usa Atalaya (administración) y quien tiene el correo (cada empleado) son personas distintas; el diseño de un solo buzón no servía para vender a organizaciones. Detalle y límites en `docs/adr/0003-buzones-invitaciones-y-administracion.md`.

**Ahora entra:**
- Varios buzones por organización, cada uno con su estado de cobertura.
- Invitación de un solo uso (vence en 48 h, revocable) → página de consentimiento → Google → confirmación. La persona invitada **no ve el panel**.
- Login de administración (contraseña por variable de entorno, límite de intentos) y auditoría persistente.
- SQLite para buzones (token cifrado), invitaciones y auditoría.
- Demo pública con 3 empleados simulados y el flujo de invitación simulado.

**Sigue sin entrar:** delegación a nivel de dominio de Google Workspace, Microsoft 365, varias organizaciones, roles múltiples, agrupación por campaña (el mismo phishing en varios buzones aparece como alertas separadas), verificación de Google.

## Decisión de proveedores de correo (17 nov)
- **Aclaración:** tener dominio propio no implica un proveedor. Una institución con dominio propio puede usar Google Workspace (Gmail) o Microsoft 365 (Exchange/Outlook). Hotmail/Outlook personal es de Microsoft, no de Google.
- **Arquitectura:** una interfaz `MailProvider` común (listar correos nuevos, leer cabeceras y metadatos, aplicar etiqueta/categoría, mover a cuarentena, estado de conexión). Gmail y Microsoft son dos implementaciones.
- **Prioridad:** se implementa primero el proveedor que usen la mayoría de las personas entrevistadas (miércoles y jueves). Si hay empate o dudas, **Gmail primero** (cuentas de prueba más fáciles).
- **Meta:** un conector funcionando de punta a punta antes de empezar el segundo.
- **En el pitch:** mostrar la arquitectura con ambos proveedores y el estado real de cada uno, sin presentar como terminado lo que no lo está.
- **Preparación permitida antes del 20** (registrar en `ESTADO_INICIAL.md`): crear el proyecto de Google Cloud en modo de pruebas y el registro de aplicación en Microsoft Entra, con cuentas de prueba propias de cada proveedor.

### Dato nuevo (18 nov): la una universidad pública usa Microsoft 365
Una guía oficial de el área de TI explica cómo activar la autenticación multifactor en las cuentas de **Microsoft 365** de la una universidad pública. Es un indicio fuerte de que al menos una universidad grande de Panamá usa Microsoft. Es **un solo dato**: lo deciden las entrevistas (una consultora de TI y una universidad privada). Si la mayoría confirma Microsoft 365, el conector prioritario pasa a ser Microsoft, y el viernes por la mañana hay que preparar el registro de la aplicación en Entra, no solo Google Cloud.

## Ampliaciones autorizadas (20 nov 2026)
Con **permiso explícito de la persona dueña del proyecto** el 20 nov 2026 entraron dos piezas que no estaban en "Entra": **campañas** (agrupar el mismo ataque en varios buzones y aislarlo con una sola acción reversible) y un **rol de supervisor de solo lectura** con reporte de la organización. Ver `docs/adr/0004-panel-de-organizacion-campanas-y-supervisor.md`.

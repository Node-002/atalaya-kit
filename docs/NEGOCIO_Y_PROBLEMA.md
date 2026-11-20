# Problema y negocio — Atalaya

> Track Build for Business: el 55 % de la nota es **problema (30 %) + negocio (25 %)**.
> Regla de oro: **nada de cifras inventadas.** Todo número debe tener fuente verificada o estar marcado como hipótesis.

## 1. El problema (30 %): claridad y tamaño
**Enunciado (borrador):** las organizaciones pequeñas reciben correos de phishing y adjuntos maliciosos, no tienen un equipo de seguridad que los revise, y dependen de que cada empleado dude a tiempo.

Qué hay que dejar claro:
- **Quién sufre:** pymes, colegios, universidades, entidades pequeñas (Panamá y Costa Rica).
- **Cuál es el dolor:** tiempo perdido, miedo a hacer clic, fraude, robo de credenciales.
- **Cuánto duele (tamaño):** *pendiente de datos reales.*

Datos a conseguir y citar (verificar fuente y fecha):
- [ ] Frecuencia de phishing/fraude por correo en Panamá, Costa Rica o LATAM (informes de organismos de ciberseguridad, bancos, CSIRT nacionales).
- [ ] Número aproximado de pymes y centros educativos en cada país (estadísticas oficiales).
- [ ] Ejemplos reales y documentados de incidentes.
- [ ] Lo que dijeron 2–3 personas entrevistadas (ver guion abajo).

## 2. Cliente y propuesta de valor
- **Cliente que paga:** el responsable de TI o administrador de la organización (no el empleado).
- **Usuario final:** el empleado cuyo correo se protege.
- **Valor:** menos riesgo con poco esfuerzo, explicaciones claras en español, privacidad (el supervisor ve alertas, no correos).
- **Alternativas actuales:** protección incluida en Google/Microsoft, productos empresariales caros, o nada. Ver `docs/COMPETENCIA.md`.

## 3. Negocio y monetización (25 %) — hipótesis a validar
Todo lo siguiente son **hipótesis**, no hechos:

| Pregunta | Hipótesis inicial | Cómo validarla |
|---|---|---|
| ¿Quién paga? | La organización, por buzón protegido al mes | Entrevistas: ¿pagarían? ¿cuánto? |
| ¿Cómo se cobra? | Suscripción mensual por buzón, con prueba gratuita | Comparar con precios de competidores (verificados) |
| ¿Cómo se llega al cliente? | A través de proveedores de internet/nube y de integradores locales, o directo a colegios y pymes | Preguntar en Dojo/RACSA si hay interés |
| ¿Qué cuesta? | Llamadas a la IA por correo analizado, hosting, soporte | Medir el costo real de las llamadas durante las pruebas |
| ¿Qué la hace defendible? | Español y contexto local, privacidad por diseño, sencillez | Comparación con competidores |

Para el pitch: un **precio hipotético** con su cálculo de costo por buzón (con datos medidos de tus pruebas), marcado como estimación.

## 4. Demo que funcione (25 %)
- Modo demo público con bandeja simulada (ver `docs/MVP_ALCANCE.md`).
- Recorrido completo sin fallos: phishing → alerta → aprobación → correo en cuarentena.
- Video de respaldo grabado.
- Resultado medible sobre ~30 correos de prueba.

## 5. Experiencia de usuario (20 %)
- Panel limpio con un solo objetivo por pantalla.
- Mensajes de alerta en español sencillo (sin jerga).
- Accesibilidad básica: contraste, tamaños, teclado.
- Estados claros: conectada / desconectada / en revisión.
- Aviso de privacidad visible y botón para desconectar.

## 6. Guion de entrevista (15–20 min, a 2–3 personas de TI o administración)
1. ¿Cuántas personas usan correo en su organización y quién se encarga de la seguridad?
2. ¿Han recibido correos sospechosos? ¿Cómo lo manejan hoy?
3. ¿Ha habido algún incidente (clic equivocado, robo de cuenta, fraude)? ¿Qué costó?
4. ¿Qué herramientas usan hoy para proteger el correo?
5. Si una herramienta revisara los correos automáticamente, ¿qué le preocuparía? (privacidad, permisos, falsos positivos)
6. ¿Preferiría que el sistema actúe solo o que le pida aprobación?
7. ¿Quién decide la compra y con qué presupuesto aproximado?
8. ¿Cuánto pagaría por buzón al mes por algo así? ¿Y qué sería "demasiado caro"?
9. ¿Qué tendría que pasar para que lo adoptara?
10. **¿Qué correo usan: Google Workspace/Gmail, Microsoft 365/Outlook u otro?** (define qué conector se prioriza)

Notas: pedir permiso para citar lo que digan, **sin grabar ni anotar nombres** si no lo autorizan.

## 7. Cómo se mapea al pitch
| Diapositiva | Criterio |
|---|---|
| Problema con datos y testimonios | Claridad y tamaño (30 %) |
| Demo en vivo y resultados medidos | Funciona (25 %) |
| Cliente, precio hipotético y canal | Negocio (25 %) |
| Pantallas, accesibilidad, lenguaje | UX (20 %) |

## Modelo de venta en el Marketplace de Dojo (17 nov)
Dojo publica lo entregado en su Marketplace, donde compran builders y empresas, y el creador se queda con el 85 % de cada venta. Esto convierte la pregunta "¿cómo se monetiza?" en algo concreto.

### Opciones de qué se vende (hipótesis, sin decidir)
| Opción | Qué es | Pros | Contras |
|---|---|---|---|
| **A. Servicio alojado por buzón** | La organización conecta sus buzones y paga una suscripción | Es el modelo que ya tenemos | Para uso público con Gmail exige verificación de Google y evaluación de seguridad; responsabilidad de privacidad alta |
| **B. Kit autoalojado** | La organización o integrador instala Atalaya con su propio proyecto de Google/Microsoft | Evita que el producto custodie cuentas de terceros; el cliente controla sus datos | Más trabajo de instalación para el cliente |
| **C. Motor de análisis para builders** | El analizador (reglas + explicación) como herramienta/MCP/API que otros desarrolladores integran | Encaja con compradores de un marketplace de builders; no maneja el correo del cliente final | Es un producto distinto de la idea original |

En el hackathon se muestra A (en modo demo) y se menciona B y C como camino de venta. **No decidir sin conocer cómo funciona la entrega y el cobro en el Marketplace** (ver preguntas en `docs/REGLAS_Y_TRACKS.md`).

### Responsabilidades si se vende (no resolverlas en 3 días, pero nombrarlas en el pitch)
- Términos de servicio y política de privacidad claros.
- Verificación de la aplicación en Google para el alcance de Gmail (para uso público).
- Cumplimiento de la ley de protección de datos del país del cliente.
- Soporte y mantenimiento (el capitán "opera" el producto).
- Pagos e impuestos para quien cobra desde Panamá.

### Preguntas nuevas para las entrevistas
- ¿Compraría una herramienta así en un marketplace o prefiere contratar a un proveedor?
- (A integradores y agencias) ¿Revenderían o instalarían una solución así a sus clientes? ¿Cuánto cobrarían por ello?
- ¿Prefieren una suscripción mensual, una licencia anual o pagar por instalación?

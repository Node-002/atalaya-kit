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
- Correo de Microsoft/Outlook/Hotmail (se menciona como siguiente paso).
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

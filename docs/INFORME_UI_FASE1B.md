# Informe — UI fase 1B (diseño fiel al prototipo + ficha técnica)

Rama: `claude/ui-fase1-849e97` (sin push ni merge). Continúa `docs/INFORME_UI_FASE1.md`. ADR nuevo: `docs/adr/0010-ficha-tecnica-de-cabeceras.md`.

## 1. Qué cambió (en el orden pedido)
1. Quitada la tarjeta roja «N correos requieren tu decisión». El número de decisiones pendientes vive en la insignia roja de «Panel de Control» del menú (y en un texto solo para lectores de pantalla).
2. Cuatro tarjetas como el prototipo (Correos Analizados, Amenazas Altas/Medias/Bajas) con icono y subtítulo `Score ≥ 60 / 30–59 / < 30` tomado de `/api/policy`. Son clicables (filtran la lista). «Bajas» cuenta riesgo bajo con alguna señal; los correos sin señales se muestran como «Limpio».
3. Pestañas segmentadas Todos / Alta / Media / Baja / Cuarentena / Legítimos con contador, mismo aspecto.
4. Búsqueda «Buscar empleado o remitente…» (nombre del buzón y dominio del remitente).
5. Menú y marca: torre grande (36×40), rótulo ATALAYA (SVG del prototipo, 129×16) y lema; ítems Panel de Control, Analítica y Tráfico, Usuarios Conectados, Historial de Amenazas, Configuración de Auditoría (solo lectura) con contadores.
6. Tarjeta de la persona: píldora «N BUZONES», avatar con iniciales, nombre y rol, «Rol activo / permisos» con líneas Habilitado/Bloqueado/Permitido según el rol real. Selector de rol solo en la demo (cookie); en modo conectado es texto fijo. En la demo la persona es «Carlos Mendoza» (simulado). Sin «SOC v3.0».
7. Tipografía: Inter 400–700 y JetBrains Mono 400–700 autoalojadas (`app/static/fonts/`, solo `.woff2` latin y latin-ext, 16 archivos, 348 KB; `NOTICE.txt` y licencias SIL OFL), `font-display: swap`, respaldos con `size-adjust`/`ascent-override`, `preload` de 3 fuentes. También en login, invite y connected.
8. «Analítica y Tráfico» con datos reales: barras apiladas por hora (24 h) o por día (7/30 d) de limpio/alta/media/baja; «Vectores detectados» agrupando señales por tipo; tarjetas de los 3 buzones con más riesgo y tabla comparativa por buzón (analizados, A/M/B, tasa de riesgo, vector principal). Sin tasa de contención, latencia ni correos/min. En la demo la ventana termina en el correo simulado más reciente (el reloj es simulado) y la página lo dice.
9. Inspector igual al prototipo: botones, «Ficha técnica del mensaje» + «Copiar IoC» (autenticación SPF/DKIM/DMARC, IP de origen y país «—», vector, Return-Path enmascarado, URL neutralizada), pestañas «Análisis Forense» («¿Por qué Atalaya detectó esta amenaza?» numerada) y «Cabeceras SMTP». En pantalla ancha abre el primer correo por defecto.
10. Reglas que siguen: CSP intacta, sin `innerHTML` ni CDN, umbrales de solo lectura, nunca cuarentena automática, motivo obligatorio, supervisor 403, informes PDF, conteos reales, aviso de demo.

Desviaciones deliberadas respecto al prototipo: textos de 12 px mínimo (el prototipo usa 10–11 px; accesibilidad); sin «Repetir Intro» (en su lugar «Reiniciar demostración», solo demo); sin selector de organización ni departamentos; sin asunto; «Auditar» lleva a los correos del buzón; sin splash; el detalle se desliza sobre la lista entre 800 y 1099 px y es pantalla propia en móvil (el prototipo se superpone a esos anchos).

## 2. Qué se guarda ahora (resumen; detalle en el ADR 0010)
Antes: veredicto, señales, hash, estado. **Ahora además**, cifrado y por alerta (≤ 2 KB): SPF/DKIM/DMARC, IP de origen, Return-Path con la parte local enmascarada (`ab***@dominio`), host de enlaces neutralizado (sin ruta), dominio de Reply-To, vector de ataque y hasta 12 cabeceras saneadas (Received como `from host [ip] by host`, DKIM solo `d=`/`s=`, Message-ID solo dominio…). **Nunca** asunto, cuerpo, adjuntos ni direcciones completas. País: no se consulta. Actualizados: README, `docs/ETICA_LEGAL_SEGURIDAD.md` e `invite.html` (consentimiento). `CLAUDE.md` no se tocó: dice «solo veredicto, señales, ID/hash y estado», así que **queda desactualizado** y la persona debe decidir si lo cambia.

## 3. Pruebas y medidas
- `pytest`: 455 pasan (444 + 9 de `test_ficha.py` + 2 de fuentes/secciones). Una prueba existente (`test_security`) se ajustó para no leer los `.woff2` como texto.
- `test_ficha.py`: asunto, cuerpo, direcciones completas, firma DKIM y rutas de URL no aparecen en lo guardado; 500 cabeceras `Received` y valores con `<script>`, `{{x}}` y 20 KB no rompen, no inyectan y respetan los topes; IP privada ignorada y la pública más antigua gana; alertas viejas sin ficha cargan y generan informe; el PDF resiste marcado hostil; la API nunca expone asunto ni cuerpo.
- `ruff check .`, `bandit`, `pip-audit`, `gitleaks`: limpios.
- axe-core (wcag2a/aa, 2.1aa, buenas prácticas) en Panel, detalle, SMTP, Analítica, Usuarios, Historial, Auditoría y Supervisor a 1366/800/412: 0 violaciones; flujo de motivo, CSV, supervisor y Esc/foco, y consola sin errores.
- Lighthouse (`127.0.0.1:8060`): escritorio **100/100/100/100** (3 corridas, CLS 0,004–0,013); móvil rendimiento 96–99, accesibilidad/buenas prácticas/SEO 100, CLS 0–0,016. El CLS salía a 0,078 por la carga tardía de fuentes y por huecos de tamaño distinto (campañas, filtros que pasaban a dos líneas): se reservaron los huecos y la búsqueda quedó bajo las pestañas, como en el prototipo.
- Escala y hostilidad de fase 1 (200 buzones) se revisaron con la versión anterior; con la nueva no repetí el recorrido de 200 buzones simulados.

## 4. Capturas
`docs/img/ui-fase1b/comparacion-<ancho>-<vista>.png` (prototipo a la izquierda, resultado a la derecha): panel, detalle, SMTP, analítica, usuarios, historial, auditoría, supervisor, y menú en 412.

## 5. No pude verificar
- Cabeceras reales de Gmail (solo demo y mensajes de prueba): el análisis es de mejor esfuerzo.
- Revisión legal de los textos de privacidad y consentimiento.
- Solo Chrome; 800 y 412 px emulados. Los comparativos son a ojo.
- La tabla de analítica con 200 buzones y la gráfica con datos de varios días (la demo tiene un solo día).
- Descarga real del CSV en el navegador (solo su contenido).

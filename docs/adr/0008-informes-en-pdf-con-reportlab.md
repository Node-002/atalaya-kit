# ADR 0008 — Informes en PDF con ReportLab

- **Fecha:** 2026-11-21
- **Estado:** aceptada.

## Contexto
Los informes salían como texto plano (`.md`). Quien supervisa los quiere en PDF, con plantilla, para leerlos y archivarlos. Solo PDF (no Word).

## Decisión
1. **ReportLab 5.1.0** (con Pillow 13.0.0), generando el PDF en el servidor, en `app/report_pdf.py`. Se pidió por `?formato=pdf` en los mismos dos endpoints de siempre (`/api/alerts/{id}/report` y `/api/org-report`); sin el parámetro siguen saliendo en texto. `formato` solo admite `txt` o `pdf` (otro valor da 422). Son `GET` de solo lectura: el supervisor puede descargarlos; en modo Gmail sin sesión dan 401 como el resto de la API.
2. **Plantilla:** encabezado con la marca (escudo dibujado con vectores, sin archivos de imagen), resumen con cifras, tablas, «Cómo leer este informe», bloque de conformidad y pie «Página x de y». El rojo se usa solo para riesgo alto o decisiones pendientes.
3. **Fuente:** Helvetica incorporada en el PDF (en Render/Linux no hay Arial). No dibuja letras fuera de Latin-1: se sustituyen por `[U+XXXX]`. Así un dominio con una «а» cirílica sale `b[U+0430]ncogeneral`, que en un informe de seguridad es justo lo que hay que ver.
4. **Escape del marcado:** `Paragraph` de ReportLab interpreta marcado tipo HTML. Todo texto de un correo o de una persona (dominio, etiqueta de buzón, motivo, explicación, nombre de la organización, actor del registro) pasa por `_safe`, que escapa `<`, `>` y `&` y elimina caracteres de control. Solo los textos fijos de la plantilla usan `pm()` con negritas.
5. **Privacidad:** el PDF no incluye cuerpos ni adjuntos (Atalaya no los guarda): solo dominio, señales, decisiones y motivos.
6. **Topes:** 60 buzones, 100 decisiones y 50 entradas del registro, con la nota «se muestran…». Con 200 buzones y cientos de decisiones se genera en pocos segundos.
7. **Descarga, no visor:** los botones de la interfaz piden `download=true` (`Content-Disposition: attachment`), con `nosniff`. La CSP `default-src 'self'` no se toca.

## Consecuencias / riesgos
- **Dependencia nueva** (ReportLab y Pillow): `pip-audit` y la fijación de versión en `requirements.txt` la cubren; hay que revisar sus avisos de seguridad al actualizar. `pypdf` solo se usa en pruebas (`requirements-dev.txt`).
- **Riesgo de inyección de marcado** si alguien añade un texto sin pasar por `_safe`: las pruebas (`test_report_pdf.py`) cubren `<b>`, `<font>`, `&nbsp;`, `</para>` y `{{x}}`, pero cada campo nuevo debe usar `_safe`.
- El nombre del archivo lo fija el servidor (`informe-<id>.pdf`; el id ya existe en el almacén) y no se puede manipular desde la URL.
- **No verificado:** que el visor de Chrome/Edge abra el PDF en línea (sin `download`) bajo la CSP; el navegador integrado de la herramienta lo trata como descarga. Por eso la interfaz solo ofrece descarga.

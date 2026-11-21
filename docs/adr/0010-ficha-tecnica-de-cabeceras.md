# ADR 0010 — Ficha técnica de cabeceras (lista blanca de metadatos)

- **Fecha:** 2026-11-21
- **Estado:** aceptada (decisión del usuario, que quiere ver esa ficha en el panel).

## Contexto
Hasta ahora Atalaya guardaba solo veredicto, señales, hash y estado. El diseño aprobado muestra una «ficha técnica» (autenticación, IP de origen, vector, Return-Path, URL, cabeceras SMTP). Esos datos salen de las cabeceras, que son dato hostil y a veces personales.

## Decisión
1. Se guarda, dentro de la alerta cifrada (`Alert.ficha`, opcional), SOLO esta lista blanca (`app/ficha.py`): resultado de SPF/DKIM/DMARC (`pass/fail/none/softfail/neutral…`); IP de origen (la IP pública más antigua de la cadena `Received`; sin consultar nada externo); Return-Path con la parte local enmascarada (`ab***@dominio`); host de cada enlace neutralizado, sin ruta ni parámetros (`hxxps://host[.]tld`); dominio de Reply-To; vector de ataque; y cabeceras saneadas: Authentication-Results y Received-SPF (con direcciones enmascaradas), DKIM-Signature solo `d=` y `s=` (nunca `b=`), Return-Path enmascarado, cada Received como `from host [ip] by host`, Message-ID solo dominio.
2. **Nunca** se guarda asunto, cuerpo, adjuntos ni direcciones de correo completas. Se quitan caracteres de control y `<>`; máximo 12 cabeceras, 5 Received, 5 hosts, 240 caracteres por línea y 2 KB por ficha (se recorta si se pasa).
3. **País:** no se consulta ni se incluye base de geolocalización; la interfaz muestra «—» y lo dice.
4. El vector principal lo calcula el código (señal de más peso), no la IA. `Signal.vector` y `Alert.vector` son campos calculados, no guardados aparte.
5. Alertas anteriores no tienen ficha: se muestra «Sin datos técnicos guardados» y nada se rompe. La ficha viaja en los informes (texto y PDF) y en la API de alertas (administración y supervisor, como el resto).
6. En la demo, el proveedor simulado genera cabeceras coherentes con cada ataque, con IP de redes de documentación (RFC 5737) que no existen en internet.
7. Todo se muestra con `textContent` (la interfaz) o escapado (`_safe`, PDF). Pruebas: `app/tests/test_ficha.py`.

## Consecuencias / riesgos
- Se amplía lo que Atalaya guarda: README, `docs/ETICA_LEGAL_SEGURIDAD.md` y el texto de consentimiento de `invite.html` se actualizaron. La IP puede ser dato personal en algunas jurisdicciones; queda cifrada y se borra al desconectar el buzón. **No lo revisó una persona abogada.**
- El enmascarado deja las dos primeras letras de la parte local; si se quiere más privacidad, enmascarar todo es un cambio de una línea.
- Las cabeceras de un proveedor real (Gmail) varían: el análisis es de mejor esfuerzo y puede dejar campos vacíos.
- **No verificado** con un buzón real de Gmail (solo con la demo y mensajes de prueba).

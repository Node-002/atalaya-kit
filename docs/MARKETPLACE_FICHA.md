# Ficha del Marketplace: Atalaya — kit autoalojado

> **Estado honesto:** el kit se probó con pruebas automáticas y un arranque local en Python. **No se ha probado con una organización de Google Workspace real**, no hay clientes ni ingresos, y el precio es una **hipótesis con huecos**.

## En una frase
Tu propia copia de Atalaya, que vigila el correo de tu organización, explica en español por qué desconfía de un mensaje y, **solo con aprobación humana**, lo saca de la bandeja. Tú la instalas en tu infraestructura: **nosotros nunca vemos tus correos, tokens ni claves**.

## Qué incluye
- El código de Atalaya (licencia **AGPL-3.0**) y el kit: `Dockerfile` (etapa `kit`), `docker-compose.yml`, `Caddyfile` de ejemplo con HTTPS automático y `.env.kit.example` sin valores.
- Guía paso a paso en español para una persona de TI: [INSTALACION.md](INSTALACION.md) (incluye evaluación en 15 minutos en `localhost`).
- Herramientas: verificador de instalación, respaldo y restauración, procedimiento de actualización.
- Panel de organización: alertas con señales verificables (SPF/DKIM/DMARC, dominios parecidos, enlaces, «responder a»), campañas, roles de administración y supervisión de solo lectura, informes en PDF.
- Cuarentena **reversible** (quitar de la bandeja + etiqueta), siempre con aprobación; nunca borra ni envía correos.

## Qué requiere
- Una organización con **Google Workspace** y una persona con permisos para crear un proyecto de Google Cloud y marcar la aplicación como «Interna».
- Un servidor con Docker (Linux recomendado) y, para uso real, un dominio con HTTPS.
- (Opcional) Una clave de Anthropic para explicaciones con IA.

## Qué NO incluye (límites honestos)
- **Solo Gmail/Google Workspace hoy.** Microsoft 365 está en hoja de ruta ([ADR 0012](adr/0012-kit-autoalojado-en-lugar-de-servicio-alojado.md)) y **no está construido**.
- **Sin soporte garantizado:** no hay acuerdo de nivel de servicio ni atención 24 h. La ayuda de instalación está por definir.
- **No analiza adjuntos** ni reputación de enlaces; no detecta fraudes sin señales técnicas.
- La medición de detección usa un corpus **sintético** (21 de 24 intentos detectados; 3 de 24 legítimos marcados de más); no es una medición con correos reales ([RESULTADOS_PRUEBAS.md](RESULTADOS_PRUEBAS.md)).
- No es un servicio alojado: **tú** operas el servidor, los respaldos y las actualizaciones.
- No es asesoría legal; los textos de privacidad y términos son borradores sin revisión de una persona abogada.

## IA real (opcional) y su aviso de privacidad
Apagada por defecto: las explicaciones salen de plantillas y no se envía nada fuera. Si la organización la activa, para cada correo analizado se **envía a un proveedor externo (Anthropic)** un texto **enmascarado** (dominio del remitente, asunto de hasta 200 caracteres, dominios de enlaces y hasta 1 500 caracteres de texto). El enmascarado es de mejor esfuerzo, no una garantía. **No se ha probado con una cuenta de pago real.**

## Licencia
**AGPL-3.0** (texto en [LICENSE](../LICENSE)) **más licencia comercial** para quien necesite usarlo en un producto cerrado o sin las obligaciones de la AGPL. Las condiciones de la licencia comercial están por definir ([LICENCIA_OPCIONES.md](LICENCIA_OPCIONES.md)).

## Precio — HIPÓTESIS (nada validado)
No hay precio definido. Hay que medir el **costo de IA por correo** (la API aún no tiene saldo) y comparar con precios **verificados** de la competencia. No se inventan cifras.

| Concepto | Qué se cobraría | Precio | Cómo se fijaría |
|---|---|---|---|
| Licencia del kit (única o anual) | Software + guía + actualizaciones del repositorio | **por definir** | Entrevistas y encuesta; comparar con la competencia |
| Licencia comercial (sin AGPL) | Derecho a usarlo en un producto cerrado | **por definir** | Caso por caso |
| Ayuda de instalación | Acompañamiento remoto | **por definir** | Tiempo real de una primera instalación (sin medir) |
| IA real | La organización paga a su proveedor con su propia clave | Sin costo para nosotros; costo por correo **por medir** | Medir con saldo en la API |
| Actualizaciones y soporte | Sin garantía hoy | **por definir** | Decidir si se ofrece y con qué alcance |

El Marketplace de Dojo deja al creador el 85 % de cada venta (según [PREGUNTAS_ORGANIZADORES.md](PREGUNTAS_ORGANIZADORES.md)); **cómo se entrega y cobra ahí un producto autoalojado sigue sin respuesta por escrito.**

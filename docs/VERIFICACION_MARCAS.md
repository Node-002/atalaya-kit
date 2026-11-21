# Verificación de dominios oficiales de las marcas (21 nov 2026)

Antes, la lista de marcas de `BRANDS` (`app/analyzers.py`) se había escrito de memoria. Aquí queda lo verificado con fuentes públicas y lo que **no** se pudo confirmar.

## Método (y su límite)
Un dominio solo se añadió si se cumplió al menos una de estas pruebas, hechas el 21 nov 2026:
- **Certificado TLS con titular:** el certificado que sirve `https://<dominio>` trae el nombre de la empresa en el campo `O=` (por ejemplo `O=BANISTMO S.A.`), o el dominio aparece en la lista de nombres (SAN) de un certificado de esa empresa. Es la prueba más fuerte: una autoridad validó a la organización.
- **Infraestructura propia de la marca:** certificado emitido para `*.peg.a2z.com` (infraestructura interna de Amazon).
- **Lista publicada por la propia marca:** `https://www.google.com/supported_domains`.
- **Sitio oficial que enlaza al dominio** (por ejemplo `yappy.com.pa` enlaza a `bgeneral.com`).

Límite: no se consultó WHOIS ni los DNS internos de cada empresa, y un certificado sin `O=` (validación solo por dominio) únicamente prueba control del dominio; esos casos se marcan abajo. La lista debe revisarse cada cierto tiempo.

## Cambios clave
- **Faltaba `bgeneral.com`**, el dominio principal real de Banco General (`https://www.bgeneral.com`, certificado `O=BANCO GENERAL S.A.`). Un correo de Banco General desde ese dominio salía como `display_name_brand`: falso positivo en demo. Se añadió también la palabra de marca `bgeneral` (así `bgeneral-clientes.example` se detecta).
- **Google** pasó de 5 a 190 dominios (todos los de `supported_domains`): antes `google.es`, `google.com.mx`, etc. se marcaban como imitación.
- **Amazon** pasó de 5 a 23 dominios regionales; **DHL** de 4 a 91; **PayPal** de 2 a 77 (incluye `paypal-communications.com`, usado para correo masivo); **Facebook** gana `facebook.net`.
- Marcas nuevas: Instagram, WhatsApp, LinkedIn, DocuSign, Bancolombia, Scotiabank.

## Tabla marca → dominios verificados → fuente
| Marca | Dominios verificados | Fuente (lo que se comprobó) |
|---|---|---|
| Banco General | bancogeneral.com, bgeneral.com, banco-general.com, bgeneral.fi.cr, bgeneralcr.com | https://www.bgeneral.com (cert `O=BANCO GENERAL S.A.`, SAN con banco-general.com y bancogeneral.com); https://bgeneral.fi.cr (mismo titular, SAN con bgeneralcr.com). bancogeneral.com sirve el mismo sitio. |
| Yappy | yappy.com.pa | https://yappy.com.pa (cert `O=BANCO GENERAL S.A.`) |
| BNCR | bncr.fi.cr | https://www.bncr.fi.cr (cert `O=Banco Nacional de Costa Rica`) |
| BAC | baccredomatic.com, baccredomatic.cr, baccredomatic.sv, bac.net | https://baccredomatic.com (cert `O=BAC International Bank`, SAN con .cr, .sv y pa.bac.net) |
| Banistmo | banistmo.com, banistmo.com.pa | https://www.banistmo.com (cert `O=BANISTMO S.A.`, SAN con .com.pa) |
| Banco Nacional de Panamá | banconal.com.pa | https://www.banconal.com.pa (cert `O=Banco Nacional de Panamá`) |
| Davivienda | davivienda.com, davivienda.cr, davivienda.com.pa, davivienda.hn, davivienda.com.hn, davivienda.com.sv | https://www.davivienda.com (`O=BANCO DAVIVIENDA S A`), https://www.davivienda.cr (`O=BANCO DAVIVIENDA COSTA RICA S.A.`); .com.pa/.hn/.sv en el SAN del certificado de https://davivienda.com.pa, cuyo sitio enlaza a davivienda.com |
| Tigo | tigo.com.pa, tigo.com, tigo.cr (ya estaban) | https://www.tigo.com.pa (cert `O=Millicom International Services LLC`). tigo.com y tigo.cr: ver «sin confirmar». |
| Google / Gmail | google.com, gmail.com, googlemail.com, google-analytics.com y los 186 `google.<país>` | https://www.google.com/supported_domains (lista de Google); google-analytics.com: SAN con googleoptimize.com y googletagmanager.com |
| Microsoft / Outlook / Office 365 | microsoft.com, microsoft365.com, microsoftstore.com, microsoftonline.com, outlook.com, office.com, office365.com (+ live.com y hotmail.com, que ya estaban) | https://www.microsoft.com, https://microsoft365.com, https://microsoftstore.com (`O=Microsoft Corporation`); https://outlook.office365.com (SAN con office365.com, outlook.com, microsoftonline.com) |
| Netflix | netflix.com, netflix.ca | https://www.netflix.com (`O=Netflix`, SAN con netflix.ca) |
| Dropbox | dropbox.com, dropboxmail.com | https://www.dropbox.com (`O=Dropbox, Inc`); dropboxmail.com redirige a https://www.dropbox.com/business/ |
| PayPal | paypal.com, paypal.me, 49 `paypal.<país>`, 31 `paypal-*` (p. ej. paypal-communications.com, paypal-mktg.com) | https://paypal.com (`O=PayPal, Inc.`, su SAN lista todos) |
| Apple / iCloud | apple.com, apple.com.cn, apple.co, apple.news, icloud.com, icloud.com.cn | https://www.apple.com, https://www.icloud.com, https://apple.co, https://apple.news (`O=Apple Inc.`) |
| Amazon | amazon.com, es, com.mx, co.uk, de, fr, it, ca, com.br, co.jp, jp, in, co.in, com.au, nl, se, pl, sg, ae, sa, com.tr, com.be, eg | https://amazon.<país> con certificado de `*.peg.a2z.com` (infraestructura de Amazon); el SAN de https://amazon.com lista co.uk, de, co.jp, com.au, jp |
| Facebook / Meta | facebook.com, facebook.net, facebookmail.com, fb.com, meta.com, messenger.com | https://www.facebook.com, https://connect.facebook.net, https://www.messenger.com, https://www.meta.com (`O=Meta Platforms`); facebookmail.com y fb.com redirigen a facebook.com |
| DHL | dhl.com y 90 `dhl.<país>`, dhl-usa.com, dhlegypt.com | https://www.dhl.es (cert `O=Deutsche Post AG`, su SAN trae la lista) |
| Cable & Wireless Panamá | cwpanama.com, cwpanama.net (ya estaban) | Panamá América: https://panamaamerica.com.pa/economia/plataforma-google-apps-ya-esta-en-cwpanamanet-556379 (webmail.cwpanama.net y www.cwpanama.com); el certificado de https://cwpanama.net cubre *.cwpanama.com |
| WhatsApp (nueva) | whatsapp.com, whatsapp.net, wa.me | https://www.whatsapp.com (`O=Meta Platforms`) |
| Instagram (nueva) | instagram.com | https://www.instagram.com (`O=Meta Platforms`) |
| LinkedIn (nueva) | linkedin.com | https://www.linkedin.com (`O=Linkedin Corporation`) |
| DocuSign (nueva) | docusign.com, .net, .ca, .co.uk, .com.au, .com.br, .com.es, .de, .fr, .in, .it, .jp, .mx, .nl, .sg | https://www.docusign.com y https://www.docusign.net (`O=DocuSign`) |
| Bancolombia (nueva) | bancolombia.com | https://www.bancolombia.com (`O=BANCOLOMBIA S.A.`) |
| Scotiabank (nueva) | scotiabank.com, scotiabank.ca, scotiabank.com.pa, scotiabankfc.com | https://www.scotiabank.com (`O=The Bank of Nova Scotia`, SAN con esos) |

## Sin confirmar (no se añadieron o se dejaron como estaban)
- **Tigo** en otros países (`tigo.com.gt`, `.sv`, `.hn`, `.co`, `.py`, `.bo`): tienen certificado, pero ninguno con titular y no hallé una página de Millicom que los liste. No se añadieron. `tigo.com` y `tigo.cr` ya estaban; sus certificados no traen titular (`tigo.com` redirige a millicom.com), así que su titularidad es probable pero **sin confirmar**.
- **Cable & Wireless Panamá:** `cwpanama.com` no respondió por HTTPS el 21 nov y la fuente es una nota de prensa antigua; la marca actual puede usar otro dominio. Se dejó lo que había, **vigencia sin confirmar**. `cwp.com.pa` no resuelve.
- **Apple:** `cdn-apple.com` y otros dominios técnicos (`mzstatic.com`…): sin titular, no añadidos.
- **Microsoft:** `microsoftonline-p.com` sin titular visible, no añadido. `live.com` y `hotmail.com` se dejaron como estaban (no contienen la palabra de marca, no afectan).
- **Facebook:** `fbcdn.net`, `fbsbx.com` (CDN): no contienen la palabra de marca, no se añadieron.
- **Dropbox:** `dropbox.co.in`, `dropbox.jobs`, `dropboxteam.com` solo aparecen en el SAN de dropboxmail.com (sin titular), no añadidos.
- **Amazon:** otros países (`amazon.com.co`, `amazon.cl`…) no se probaron.
- **BNCR:** su certificado también cubre `bnenlinea.com`, `bndesarrollo.com` y `bnonline.fi.cr`, pero no contienen la palabra de marca; no se añadieron.

## Dominios dejados fuera a propósito (alojamiento de terceros)
Cualquiera puede publicar contenido en ellos; marcarlos como oficiales abriría un hueco. Ninguno está en `BRANDS` (una prueba lo exige): `amazonaws.com` (buckets S3), `amazonses.com` (envío masivo de cualquier cliente), `dropboxusercontent.com` (archivos de usuarios), `onmicrosoft.com` y `sharepoint.com` (cada cliente crea el suyo), `googleusercontent.com`, `appspot.com`, `web.app`, `blogspot.com`, `github.io`. Como ninguna de esas palabras es exactamente la marca, la regla `lookalike_domain` tampoco los marca por sí misma.

## Marcas valoradas y no añadidas
- **Zoom** y **Adobe:** palabras comunes en español (zoom de cámara, adobe de construcción); la regla de «palabra completa» daría falsos positivos con negocios legítimos. Decisión conservadora; añadirlas exigiría ajustar reglas, fuera de esta tarea.
- **Otros bancos** (Banco de Bogotá, BCR, Banesco, Multibank, Global Bank, Caja de Ahorros…): no se verificaron; candidatos para una próxima ronda.

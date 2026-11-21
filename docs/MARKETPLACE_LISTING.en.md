# Marketplace listing: Atalaya — self-hosted kit

> Versión en español: [MARKETPLACE_FICHA.md](MARKETPLACE_FICHA.md).

> **Honest status:** the kit was tested with automated tests and a local Python start-up. **It has not been verified with a real Google Workspace organization**, there are no customers or revenue, and the price is a **hypothesis with gaps**.

## In one sentence
Your own copy of Atalaya, which watches your organization's email, explains in plain language why it distrusts a message and, **only with human approval**, moves it out of the inbox. You install it on your own infrastructure: **we never see your email, tokens or keys.**

## What is included
- Atalaya's source code (**AGPL-3.0** license) and the kit: `Dockerfile` (`kit` stage), `docker-compose.yml`, an example `Caddyfile` with automatic HTTPS and a `.env.kit.example` with no values.
- A step-by-step guide for an IT person: [INSTALLATION.en.md](INSTALLATION.en.md) (includes a 15-minute evaluation on `localhost`).
- Tools: installation verifier, backup and restore, update procedure. Start-up messages and verifier output in English (`ATALAYA_LANG=en`) or Spanish.
- Organization panel: alerts with verifiable signals (SPF/DKIM/DMARC, look-alike domains, links, "reply-to"), campaigns, administrator and read-only supervisor roles, PDF reports.
- **Reversible** quarantine (remove from the inbox + label), always with approval; it never deletes or sends email.

## What it requires
- An organization with **Google Workspace** and a person allowed to create a Google Cloud project and mark the application "Internal".
- A server with Docker (Linux recommended) and, for real use, a domain with HTTPS.
- (Optional) An Anthropic API key for AI explanations.

## What it does NOT include (honest limits)
- **The panel interface is in Spanish only today.** English is available for the documentation, the kit's start-up messages and the verifier.
- **Gmail / Google Workspace only today.** Microsoft 365 is on the roadmap ([ADR 0012](adr/0012-kit-autoalojado-en-lugar-de-servicio-alojado.md), Spanish) and **is not built**.
- **No guaranteed support:** no service-level agreement and no 24-hour help. Installation help is yet to be defined.
- **It does not analyze attachments** or link reputation, and it does not detect fraud that has no technical signals.
- Detection was measured on a **synthetic** corpus (21 of 24 attempts detected; 3 of 24 legitimate emails wrongly flagged), not on real email ([RESULTADOS_PRUEBAS.md](RESULTADOS_PRUEBAS.md)).
- It is not a hosted service: **you** operate the server, the backups and the updates.
- It is not legal advice; the privacy and terms texts are drafts not reviewed by a lawyer.

## Real AI (optional) and its privacy notice
Off by default: explanations come from templates and nothing is sent out. If the organization turns it on, for every analyzed email a **masked** text is **sent to an external provider (Anthropic)**: sender domain, subject of up to 200 characters, link domains and up to 1,500 characters of text. Masking is best effort, not a guarantee. **It has not been tested with a real paid account.**

## License
**AGPL-3.0** (text in [LICENSE](../LICENSE)) **plus a commercial license** for anyone who needs to use it in a closed product or without the AGPL obligations. Commercial license terms are yet to be defined ([LICENCIA_OPCIONES.md](LICENCIA_OPCIONES.md)).

## Price — HYPOTHESIS (nothing validated)
There is no defined price. The **AI cost per email** must be measured first (the API account has no balance yet), and compared with **verified** competitor prices. No figures are invented.

| Item | What would be charged | Price | How it would be set |
|---|---|---|---|
| Kit license (one-off or yearly) | Software + guide + repository updates | **to be defined** | Interviews and survey; compare with competitors |
| Commercial license (no AGPL) | Right to use it in a closed product | **to be defined** | Case by case |
| Installation help | Remote assistance | **to be defined** | Real time of a first installation (not measured) |
| Real AI | The organization pays its provider with its own key | No cost to us; cost per email **to be measured** | Measure with API balance |
| Updates and support | No guarantee today | **to be defined** | Decide whether and how much to offer |

The Dojo Marketplace leaves the creator 85 % of each sale (per [PREGUNTAS_ORGANIZADORES.md](PREGUNTAS_ORGANIZADORES.md)); **how a self-hosted product is delivered and paid for there has no written answer yet.**

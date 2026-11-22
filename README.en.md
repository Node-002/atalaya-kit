# Atalaya — English summary

> Versión principal en español: [README.md](README.md). The panel interface is in Spanish only; this page and the kit documents are available in English.

Atalaya watches the email of small organizations, explains in plain language why it distrusts a message and, **only with a person's approval**, moves it out of the inbox. It never deletes or sends email.

## Installation for organizations

Any organization with **Google Workspace** can install its own copy of Atalaya on its own infrastructure, with its own Google application marked "Internal" and its own keys; **we never see its email, tokens or keys**. The kit includes `docker-compose.yml` (the `kit` stage of the `Dockerfile`), an example `Caddyfile` with automatic HTTPS, `.env.kit.example`, tools in `tools/kit/` (verifier, backup, restore) and a step-by-step guide: [docs/INSTALLATION.en.md](docs/INSTALLATION.en.md), including a 15-minute evaluation on `localhost`. Start-up messages and the verifier print in English with `ATALAYA_LANG=en` (Spanish by default). Listing and honest limits: [docs/MARKETPLACE_LISTING.en.md](docs/MARKETPLACE_LISTING.en.md). Rationale and roadmap (Microsoft 365, hosted service later): [ADR 0012](docs/adr/0012-kit-autoalojado-en-lugar-de-servicio-alojado.md) (Spanish).

**Guided install:** `tools/kit/instalar.sh` (Linux/macOS) or `.\tools\kit\instalar.ps1` (Windows) asks the questions, generates the keys and configuration, starts Docker Compose and verifies at the end; the manual guide remains option B ([docs/INSTALLATION.en.md](docs/INSTALLATION.en.md), [ADR 0014](docs/adr/0014-asistente-de-instalacion-guiado.md), in Spanish). Tested with automated tests and a fake `docker`, and the kit started with real Docker Desktop on Windows (container "healthy", with test keys); it was **not** tested with a real Google Workspace organization.

**Status:** tested in Python (start-up, preflight checks and automated tests); **not verified with a real Google Workspace organization**, and the `kit` CI job exercises Docker/Compose/Caddy; the Google Cloud steps were not run with a real organization. The public demo is unchanged: it remains demo mode only.

## Known limits
- Gmail / Google Workspace only; Microsoft 365 is on the roadmap, not built.
- No attachment analysis and no link-reputation lookups.
- Detection was measured on a synthetic corpus we wrote (62 emails: 27 of 30 attempts detected, 3 of 32 legitimate emails wrongly flagged; reproduce with `python -m app.evaluate`); part of the improvement comes from cases written for new features, so it is not a real-email measurement.
- The optional AI explanation sends masked text to an external provider when enabled and has not been tested with a real paid account.
- No guaranteed support. Pricing is an undefined hypothesis.

## Who is responsible for what
Atalaya is **not a service we run**: it is software that each organization installs and runs on **its own servers**. Therefore:

| What | Who |
|---|---|
| Installing, updating and operating the server | The **organization** that installs it |
| Storing and protecting the data (the database and keys live on its server) | The **organization** |
| Deciding which mailboxes to connect and informing the people whose email is monitored | The **organization** |
| Complying with the laws that apply to it (data protection, labor, etc.) | The **organization** |
| Hosting the service, receiving organizations' email, tokens or keys | **Nobody outside it**: the Atalaya team neither receives nor holds them |
| Support, availability, updates or guaranteed results | **Not offered**: the software is provided "as is" |

It is released under AGPL-3.0, whose sections 15 and 16 disclaim warranties and limit liability for damages. The terms of use and privacy policy (in Spanish, in `docs/`) are **drafts not reviewed by a lawyer**. Atalaya is a support tool, not a security guarantee.

## Work before the hackathon
Before 20 November 2026 there were only ideas and documentation, no product code (`docs/ESTADO_INICIAL.md`). All the code was written on 20-22 November.

## License
**GNU AGPL-3.0** ([LICENSE](LICENSE)) plus a **commercial license** for closed-product use, agreed with the team through this repository's GitHub profile.

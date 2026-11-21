# Installing Atalaya in your organization (self-hosted kit)

> Versión en español (principal): [INSTALACION.md](INSTALACION.md). Kit start-up messages and the verifier print in English with `ATALAYA_LANG=en` (Spanish is the default). The panel interface itself is in Spanish only.

> **Honest status.** This guide was written from Google's official documentation and the kit was tested **in Python only** (automated tests and a local start-up with fake data). **It has not been verified with a real Google Workspace organization, with Docker on a real server, or with Google Cloud.** The Google Cloud steps follow the public documentation as of 21 Nov 2026; if your screen looks different, the interface has changed: follow the intent of the step. Anything we could not confirm is marked ⚠️ and listed in [section 10](#10-what-is-not-verified).

## 0. What this is

Atalaya watches your organization's email and asks for human approval before acting (it never deletes or sends email). With the **self-hosted kit** *you* install your own copy on *your* server, with *your* Google application and *your* keys. **We never see your email, your tokens or your keys.**

Why this way rather than a cloud service: [ADR 0012](adr/0012-kit-autoalojado-en-lugar-de-servicio-alojado.md) (Spanish).

## 1. Requirements

| What | Detail |
|---|---|
| A **Google Workspace** account with an **organization** | You must be able to create a Google Cloud project inside that organization and, for the "internal app" step, have administrator permissions. Personal Gmail (`@gmail.com`) has no "Internal" type: see the [evaluation mode](#evaluation-mode-15-minutes-on-localhost). |
| A server or machine with **Docker** and **Docker Compose v2** | Linux recommended (any small VPS works: 1 CPU and 1 GB of memory should be enough for dozens of mailboxes; **not measured** in a real organization). |
| A **domain with HTTPS** | For real use: `https://atalaya.yourorganization.org` pointing at the server. The kit includes Caddy, which obtains the certificate by itself (ports 80 and 443 open). To evaluate without a domain: `http://localhost:8000`. |
| A synchronized server clock (NTP) | A skewed clock once broke a real sign-in. Modern Linux does this on its own. |
| (Optional) An Anthropic API key | Only if you want AI-written explanations. It is **off** by default (see section 9). |

## Evaluation mode: 15 minutes on localhost

No domain and no server: on your own machine with Docker.

1. **Get the kit** (download the repository) and open a terminal in that folder.
2. **Google client.** Do steps 3 to 6 of [section 2](#2-create-the-google-application-once), with one difference: as the redirect URI use `http://localhost:8000/auth/google/callback` (Google allows `http` for `localhost` only). If you do not have a Workspace organization, choose **External** (testing mode) at the audience step and add your own account as a **test user**: this works with personal Gmail, with a limit of 100 test users and authorizations that Google **expires after 7 days** (from our earlier notes; ⚠️ confirm on the "Audience" screen).
3. Save the JSON as `secrets/google_client.json` (create the `secrets` folder).
4. Copy `.env.kit.example` to `.env.kit` and change: `ATALAYA_BASE_URL=http://localhost:8000`, the Fernet key, the session key and `ATALAYA_ADMIN_EMAILS` (section 4 shows how to generate the keys). Keep `ATALAYA_TRUST_PROXY=0`. Add `ATALAYA_LANG=en` if you want English start-up messages.
5. `docker compose up -d --build`
6. `ATALAYA_LANG=en python3 tools/kit/verificar_instalacion.py --env-file .env.kit` → everything `OK` (the `http://localhost` warning is normal).
7. Open **`http://localhost:8000`** (type `localhost`, **not** `127.0.0.1`: the app and Google only accept `localhost`). You should see the sign-in screen (in Spanish).

When you are done: `docker compose down -v` (deletes everything, including the data).

## 2. Create the Google application (once)

A Google Workspace administrator of the organization does this. The menu paths are those shown in Google's official documentation (sources in [section 14](#14-sources)).

1. **Create a project.** Sign in to [console.cloud.google.com](https://console.cloud.google.com) with your Workspace account. Menu **IAM & Admin > Create a Project**. Give it a name (for example "Atalaya") and, under **Location**, choose **your organization** (not "No organization"). *You should see:* the project created and selected at the top.
2. **Enable the Gmail API.** Menu **APIs & Services > Library**, search for "Gmail API" and click **Enable**. The command-line equivalent is `gcloud services enable gmail.googleapis.com`.
3. **Set up Google Auth Platform.** The consent screen now lives in **Google Auth Platform**, with the sections **Overview, Branding, Audience, Clients, Data Access** and **Verification Center**. Click **Get started** on *Overview*, fill in the application name and a contact email.
4. **Audience = Internal.** In *Audience* choose the user type **Internal**: it limits authorization to accounts of your organization. If **Internal** does not appear, the project does not belong to an organization: go back to step 1. For "Internal", Google's documentation says **verification is not required** and there is **no test-user list** (production-readiness table).
5. **Scopes (Data Access).** If the screen asks, add: `https://www.googleapis.com/auth/gmail.modify` (read and label; Atalaya **does not send or delete**, and the code has no such operations) and, for the panel sign-in, `openid` and `.../auth/userinfo.email`. Google classifies `gmail.modify` as **"restricted"**. ⚠️ For an internal application we could not confirm, in the official pages we read, whether it is exempt from restricted-scope verification and from the security assessment. What we did read: *"Internal: verification not required"*. A search-result preview of Google's documentation says restricted scopes in internally used apps "do not require further review", but we did not read it on the full page.
6. **Create the OAuth client (Clients).** In *Clients* → **Create Client** → application type **Web application**. Under **Authorized redirect URIs** add **exactly**:
   `https://atalaya.yourorganization.org/auth/google/callback`
   (your real domain). It must start with `https://`; the only exception is `http://localhost…` for evaluation. **It is a single URI**: it serves both the panel sign-in and mailbox connections. Any difference (`http`/`https`, upper case, trailing slash) gives `redirect_uri_mismatch`.
7. **Download the client JSON** (download button next to the client) and save it on the server as `secrets/google_client.json`. **It is a secret**: never push it to a repository or email it. The container user must be able to read it: `chmod 644 secrets/google_client.json` and `chmod 755 secrets`.
8. ⚠️ **Google Workspace Admin console.** The *Audience* page warns that restricted Gmail scopes "might require additional configuration by your organization's administrators". If your organization blocks third-party apps, an administrator must **allow this application** (by client ID) in the Admin console (*Security → Access and data control → API controls*). We could not verify the exact menu name; look for "API controls / third-party apps".

## 3. Prepare the server

1. Install Docker and Docker Compose v2 ([docs.docker.com/engine/install](https://docs.docker.com/engine/install/)).
2. Put the kit (clone or unpack the repository) in a folder, for example `/opt/atalaya`.
3. Create the DNS record: an A record (and AAAA if you use IPv6) for `atalaya.yourorganization.org` pointing at the server's IP. Open ports **80 and 443** in the firewall.
4. Check the time: `timedatectl` should say `System clock synchronized: yes`.

## 4. Keys and configuration

1. Copy the example file (the real one **never goes into the repository**):
   ```bash
   cp .env.kit.example .env.kit && chmod 600 .env.kit
   ```
2. Generate the two keys (do not paste them in chats or emails):
   ```bash
   docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_urlsafe(48))"
   docker run --rm python:3.12-slim sh -c "pip install -q cryptography >/dev/null 2>&1 && python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
   ```
   The first is `ATALAYA_SESSION_SECRET`; the second is `ATALAYA_FERNET_KEY`.
3. **Store the Fernet key separately** (your organization's password manager). **Without it, the stored tokens are unreadable** and every mailbox would have to be reconnected. Do not keep it next to the backups.
4. Edit `.env.kit` and replace every `CAMBIAR_...` ("change this"): `ATALAYA_BASE_URL` (your domain with `https://`), the two keys and `ATALAYA_ADMIN_EMAILS` (the Google accounts allowed into the panel, comma-separated).
5. **Proxy** (`ATALAYA_TRUST_PROXY`): see [the explanation](#reverse-proxy-and-the-login-attempt-limit).

## 5. Start it

1. Edit `Caddyfile` and replace `CAMBIAR_DOMINIO` with your domain.
2. ```bash
   docker compose --profile tls up -d --build
   ```
   *You should see:* Docker builds the image (a few minutes the first time) and starts `atalaya` and `caddy`.
3. Read the log: `docker compose logs -f atalaya`. If something is missing, **the container refuses to start** and says what: "Atalaya (kit) will NOT start: these settings are missing or wrong…" (with `ATALAYA_LANG=en`; in Spanish by default). See troubleshooting.
4. On first start Caddy requests the certificate from Let's Encrypt; it takes a few seconds if the DNS already points correctly.

## 6. Verify the installation

```bash
ATALAYA_LANG=en python3 tools/kit/verificar_instalacion.py --env-file .env.kit
```
It checks (never printing values): required variables, `https`, that the Google JSON is a *Web application* client and its redirect URI matches `ATALAYA_BASE_URL`, that `/health` answers `mode: gmail`, and the clock skew against Google. Everything should be `OK`; a `WARN` does not prevent use, a `FAIL` does.

Also open `https://atalaya.yourorganization.org/health`: it should show `{"status":"ok","mode":"gmail","auth":true}`. If it says `mode: demo`, you are running the public demo image instead of the kit.

## 7. Connect the first mailbox

1. Open `https://atalaya.yourorganization.org` → it takes you to `/login`. Choose **Iniciar sesión con Google** (sign in with Google) with an account listed in `ATALAYA_ADMIN_EMAILS`. *You should see:* the empty panel.
2. In the panel, create an **invitation** (mailbox name and area). It gives you a **single-use** link.
3. The mailbox owner (from your organization) opens the link, reads the consent notice, **authorizes with Google** and sees only a confirmation. They do not see the panel.
4. *You should see:* the mailbox in the panel and, in Gmail, the "Sospechoso" ("Suspicious") label when something needs review. Atalaya checks the inbox every 60 s (the last 7 days when connecting).

Mailboxes can only belong to accounts of your organization (an "Internal" application).

## Reverse proxy and the login attempt limit

The panel limits failed sign-in attempts **per IP address**. Behind a proxy, the client IP arrives in the `X-Forwarded-For` header, which a client can forge. Hence:

| Situation | `ATALAYA_TRUST_PROXY` | Why |
|---|---|---|
| **Behind Caddy** (the kit's `tls` profile) | **`1`** | Caddy overwrites `X-Forwarded-For` with the real IP and Atalaya takes the **last** entry, the one Caddy added (not the first, which the client writes). |
| No proxy (evaluation on `localhost`) | `0` | With `1` and no proxy, anyone could forge their IP and bypass the limit. |
| Your own proxy (nginx, Traefik, a cloud load balancer) | `1` only if it **always** adds the real IP as the **last** entry | ⚠️ With **more than one** of your own hops in front (for example CDN + proxy), the last entry would be the inner hop: the limit would count everything as one IP. There is currently no variable for multiple hops in kit mode. |

`ATALAYA_TRUSTED_HOPS` **only affects the public demo** (per-visitor limits); it is not used in the kit. The image starts with `--no-proxy-headers`: uvicorn does not trust proxy headers.

## 8. Operation

### Backup and restore
```bash
tools/kit/respaldo.sh respaldos        # creates respaldos/atalaya-YYYYMMDD-HHMMSS.db (kit running)
tools/kit/restaurar.sh respaldos/atalaya-YYYYMMDD-HHMMSS.db   # asks you to type SI (yes); replaces the current database
```
- A consistent copy of the SQLite database (SQLite backup API + integrity check). **It does not include the Fernet key.**
- The backup holds verdicts, states and **encrypted Google tokens**. To restore you need **the same** `ATALAYA_FERNET_KEY`; with another one, the tokens cannot be decrypted and mailboxes must be reconnected.
- Schedule the backup (for example with `cron`) and copy the files elsewhere. **Restoring was not tested on a real server.**

### Update
```bash
tools/kit/respaldo.sh respaldos                   # 1. back up before touching anything
git pull                                          # 2. new code (or download the new kit version)
docker compose --profile tls up -d --build        # 3. rebuild and restart (database migrations run automatically at start-up)
ATALAYA_LANG=en python3 tools/kit/verificar_instalacion.py --env-file .env.kit   # 4. all OK
docker compose logs --tail 50 atalaya             # 5. no errors
```
What to check afterwards: `/health` with `mode: gmail`, that you can sign in to the panel, and that the mailbox and alert counts match what you had. To roll back: `git checkout <previous version>`, rebuild and, if needed, run `restaurar.sh` with the backup from step 1. (If you use published images instead of building, the equivalent is `docker compose pull` and `up -d`; today the kit is built from source.)

### Where the data lives
In the `atalaya-data` volume (`/srv/data/atalaya.db` inside the container). The container's file system is read-only except that volume and `/tmp`.

## 9. What it stores and what it does not

Aligned with [POLITICA_PRIVACIDAD.md](POLITICA_PRIVACIDAD.md) (Spanish draft, not reviewed by a lawyer; with the kit, **your organization is the data controller**, not Atalaya):

| Stores (on your server, SQLite) | Does not store |
|---|---|
| Mailbox: name, address and **encrypted Google token (Fernet)** | **Email bodies and attachments** |
| Alerts (encrypted at rest): verdict, signals, sender **domain**, time, explanation, state, message hash/identifier, fingerprints for campaigns, decisions with who, when and the written reason | The subject or full sender in alerts |
| Each mailbox's area and technical header metadata (SPF/DKIM/DMARC, origin IP, etc., max. 2 KB per email, no full addresses) | Passwords |
| Invitations (link hash), sign-in audit log (with IP) | |

An email's text **does pass through the server's memory** while it is analyzed; it is not written to the database or to the logs.

**AI (optional, off by default):** with `ATALAYA_LLM=anthropic` and `ANTHROPIC_API_KEY`, for each email a **masked** text is **sent to an external provider (Anthropic)**: sender domain, subject (max. 200 characters), link domains and up to 1,500 characters of text. Masking is best effort, **not a guarantee**. Tell the people whose email is analyzed and review the provider's terms. This feature **has not been tested with a real paid account**. Without AI, the explanation comes from templates and **nothing is sent out**.

With the kit, Atalaya (the project) receives nothing from your installation: no data, no metrics, no keys.

## 10. What is NOT verified

- ⚠️ **The whole flow with a real Google Workspace organization**: creating the project, the "Internal" type, the web client, signing in and connecting mailboxes. There is no test organization. Only the Python side was verified (start-up, checks, verifier, automated tests).
- ⚠️ That an **internal** application with `gmail.modify` (a restricted scope) is exempt from verification and the security assessment: the official table says "Internal: verification not required", but we did not read a specific sentence about restricted scopes on the full documentation.
- ⚠️ Whether the 100-user cap applies to internal apps: the documentation reads "no test users" for Internal but does not say it in those words.
- ⚠️ The rule "https required except localhost" for the redirect URI: we read it only in a summary, not in the full text of the page.
- ⚠️ The exact Admin console menu for allowing the application.
- **Docker, Compose and Caddy were not run on the development machine** (no Docker there). The CI `kit` job on GitHub tests them on push; until then it is unexecuted code. What was executed: the Python start-up, the tests, `hadolint` and `actionlint`.
- Backup and restore: the SQLite copy logic was tested and the scripts were checked with `bash -n`, but they were not run against a container.

## 11. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The container exits at start with "Atalaya (kit) will NOT start…" (or "NO arranca…" in Spanish) | Something is missing; the message names each variable. Fix `.env.kit` and `docker compose up -d`. Values are never printed. |
| "The GOOGLE_CLIENT_SECRETS_FILE file … does not exist" / "cannot be read" | The JSON is not at `secrets/google_client.json`, or its owner/permissions stop user 10001 from reading it: `chmod 644`. Do not change `GOOGLE_CLIENT_SECRETS_FILE` (it is the path inside the container). |
| "The Google JSON does not include the redirect URI…" | The client's URI in Google does not match `ATALAYA_BASE_URL` + `/auth/google/callback`. Fix it under *Clients*, download the JSON again and restart. |
| Error 400 `redirect_uri_mismatch` on sign-in | Same: the URI must match **character by character** (`https`, domain, no trailing slash). Changes in Google can take a few minutes. |
| "Access blocked: this app is not authorized" / `access_denied` / `admin_policy_enforced` | (a) The account is not from your organization, or the audience is not "Internal". (b) Workspace administration blocks the app: allow it by client ID (step 8 of section 2). (c) In External testing mode, the account is not in the test-user list. |
| `invalid_grant` | The authorization code expired or was used twice (sign in again), the **server clock is skewed** (run the verifier), the user revoked access, or (External testing mode) 7 days have passed. If every mailbox fails after a restore: the Fernet key does not match. |
| Sign-in sometimes fails right when returning from Google | **Clock skew** (a real sign-in once failed because of 1.4 s). Enable NTP; `verificar_instalacion.py` measures the skew. The app tolerates 30 s when validating the token. |
| The panel does not save / "unable to open database file" / "permission denied" on `/srv/data` | The volume is not owned by user 10001. With the compose named volume this should not happen; if you use a host folder: `sudo chown -R 10001 /path/to/data`. |
| Panel sign-in fails or locks you out "for too many attempts" behind the proxy | If `ATALAYA_TRUST_PROXY=0` behind Caddy, **all** attempts appear to come from Caddy's IP and are blocked together: set `1`. If it is `1` and there is **no** proxy, the IP can be forged. Restart after changing it. |
| Cookie/session: always sent back to `/login` | You are using `http`, or a domain different from `ATALAYA_BASE_URL`. Always use the same `https` address. |
| Caddy cannot get the certificate | The DNS does not point at the server, or 80/443 are closed. `docker compose logs caddy`. |
| `/health` says `mode: demo` | You are running the public demo image; use this kit's `docker compose` (the `kit` stage). |

## 12. Uninstall and revoke

1. **Disconnect each mailbox from the panel** (revokes the token at Google and deletes the local record).
2. Each person can withdraw access at any time from their Google account: **Security → Third-party apps & services → Atalaya → Remove access** (the Spanish policy names it "Tus conexiones con apps de terceros"; ⚠️ exact English menu names not verified).
3. In Google Cloud, delete the OAuth client (*Clients*) or the whole project.
4. On the server: `docker compose --profile tls down -v` (**`-v` deletes the volume with the database**: irreversible; take a backup first if you need it) and delete the kit folder, `.env.kit` and `secrets/`.
5. If the Fernet key or the Google JSON leaked, delete the client in Google (it invalidates everything) and generate new keys.

## 13. Checklist

- [ ] Google Cloud project inside **my organization**; Gmail API enabled.
- [ ] Audience = **Internal**; client **Web application**; exact URI `https://…/auth/google/callback`.
- [ ] JSON at `secrets/google_client.json`, **outside git**.
- [ ] `.env.kit` complete, `chmod 600`, **outside git**; Fernet key **stored separately**.
- [ ] DNS points at the server; 80/443 open; clock synchronized.
- [ ] `ATALAYA_TRUST_PROXY=1` with Caddy (0 without a proxy).
- [ ] `verificar_instalacion.py` with no `FAIL`; `/health` = `mode: gmail`, `auth: true`.
- [ ] First mailbox connected and a test alert seen.
- [ ] Backup scheduled, copy kept off the server, and **restore tested** in a test environment.
- [ ] The people whose email is analyzed are informed (and AI is still off or has a notice).

## 14. Sources

Consulted on 21 Nov 2026 (official documentation; content may change):
- Google Auth Platform (sections, Internal/External/Personal): https://support.google.com/cloud/answer/15544987
- OAuth verification FAQ: https://support.google.com/cloud/answer/13463817
- Production readiness (Internal/External table): https://developers.google.com/identity/protocols/oauth2/production-readiness/overview
- Gmail API scopes (`gmail.modify` = restricted): https://developers.google.com/workspace/gmail/api/auth/scopes
- Web server flow and redirect URIs: https://developers.google.com/identity/protocols/oauth2/web-server
- Create a project and enable APIs: https://developers.google.com/workspace/guides/create-project and https://developers.google.com/workspace/guides/enable-apis
- Caddy `reverse_proxy` and `X-Forwarded-*` headers: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy (per search results of that documentation, by default Caddy trusts no proxy and ignores the `X-Forwarded-For` sent by the client; **not tested in operation**)

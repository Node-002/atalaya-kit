"""API de Atalaya.

Modos (variable ATALAYA_MODE):
- demo  (por defecto): empleados simulados, sin cuentas reales ni login. Es el unico modo publico.
- gmail: conexion real con Gmail; login de administrador obligatorio; solo uso local
  con usuarios de prueba.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import campaigns, logsafe
from app.admin import AdminAuth, build_admin_router
from app.alerts import SecurityNotifier, SmtpConfig
from app.auth import AuthContext, build_router, revoke_google_token
from app.db import Database
from app.identity import parse_email_list
from app.llm import Explainer, explainer_from_env
from app.models import Alert, Coverage, Status
from app.providers.base import MailProvider
from app.providers.demo import DemoProvider, demo_workforce
from app.registry import Registry
from app.report import build_org_report, build_report
from app.report_pdf import build_alert_pdf, build_org_pdf
from app.store import AlertStore, ReasonRequired

load_dotenv()
log = logging.getLogger("atalaya")
POLL_SECONDS = int(os.environ.get("ATALAYA_POLL_SECONDS", "60"))

STATIC_DIR = Path(__file__).parent / "static"
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
DEMO_ROLE_COOKIE = "atalaya_demo_role"


class DecisionIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class DemoRoleIn(BaseModel):
    role: Literal["admin", "supervisor"]


DEMO_MAX_INVITES = 50


class InviteIn(BaseModel):
    label: str = Field(min_length=1, max_length=80)


def _need(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno {name} (modo gmail).")
    return value


def _build_admin(registry: Registry, base_url: str) -> AdminAuth:
    """Configura el acceso de administracion desde variables de entorno (falla si es insegura)."""
    try:
        emails = parse_email_list(os.environ.get("ATALAYA_ADMIN_EMAILS", ""))
    except ValueError as exc:
        raise RuntimeError(f"ATALAYA_ADMIN_EMAILS: {exc}") from exc
    try:
        supervisors = parse_email_list(os.environ.get("ATALAYA_SUPERVISOR_EMAILS", ""))
    except ValueError as exc:
        raise RuntimeError(f"ATALAYA_SUPERVISOR_EMAILS: {exc}") from exc
    smtp = None
    if os.environ.get("ATALAYA_SMTP_HOST"):
        smtp = SmtpConfig(
            host=os.environ["ATALAYA_SMTP_HOST"],
            port=int(os.environ.get("ATALAYA_SMTP_PORT", "587")),
            user=os.environ.get("ATALAYA_SMTP_USER", ""),
            password=os.environ.get("ATALAYA_SMTP_PASSWORD", ""),
            sender=os.environ.get("ATALAYA_SMTP_FROM", ""),
        )
    notifier = SecurityNotifier(
        registry,
        contact=os.environ.get("ATALAYA_SECURITY_CONTACT") or None,
        webhook=os.environ.get("ATALAYA_ALERT_WEBHOOK") or None,
        smtp=smtp,
    )
    return AdminAuth(
        _need("ATALAYA_SESSION_SECRET"),
        registry,
        password=os.environ.get("ATALAYA_ADMIN_PASSWORD") or None,
        emails=emails,
        supervisors=supervisors,
        domain=os.environ.get("ATALAYA_ADMIN_DOMAIN") or None,
        secure_cookie=base_url.startswith("https"),
        notifier=notifier,
        failure_delay=float(os.environ.get("ATALAYA_LOGIN_DELAY", "0.4")),
        trust_proxy=os.environ.get("ATALAYA_TRUST_PROXY") == "1",
    )


def create_app(
    provider: MailProvider | None = None, explainer: Explainer | None = None
) -> FastAPI:
    logsafe.install()  # que los tokens de la URL no queden en los registros
    mode = os.environ.get("ATALAYA_MODE", "demo")
    if mode not in ("demo", "gmail"):
        raise RuntimeError("ATALAYA_MODE debe ser 'demo' o 'gmail'.")
    legacy = (
        provider is not None
    )  # un proveedor inyectado (pruebas): un solo buzon, sin login
    base_url = os.environ.get("ATALAYA_BASE_URL", "http://localhost:8000").rstrip("/")
    org_name = os.environ.get("ATALAYA_ORG_NAME") or "tu organización"

    admin: AdminAuth | None = None
    client_secrets: dict | None = None
    secrets_file: str | None = None
    if mode == "gmail" and not legacy:
        from app.providers.gmail import load_client_secrets

        secrets_file = _need("GOOGLE_CLIENT_SECRETS_FILE")
        client_secrets = load_client_secrets(secrets_file)
        fernet = Fernet(_need("ATALAYA_FERNET_KEY").encode())
        db = Database(os.environ.get("ATALAYA_DB_PATH", "data/atalaya.db"))
    else:
        fernet = Fernet(Fernet.generate_key())
        db = Database(":memory:")
    registry = Registry(db, fernet)
    if mode == "gmail" and not legacy:
        admin = _build_admin(registry, base_url)

    demo_like = mode == "demo" or isinstance(provider, DemoProvider)
    if explainer is None:
        # demo publica: resumen simulado (no gasta saldo). Conectado: IA solo si se activa.
        explainer = explainer_from_env("simulated" if demo_like else "off")
    store = AlertStore(
        provider,
        explainer,
        os.environ.get("ATALAYA_LLM_POLICY", "flagged"),
        repo=registry if (mode == "gmail" and not legacy) else None,
    )

    seed_ids: set[str] = set()
    make_provider = None
    if not legacy and mode == "demo":
        for mailbox_id, label, prov in demo_workforce():
            registry.add_mailbox(
                label, prov.account_name(), "demo", consent=True, mailbox_id=mailbox_id
            )
            store.add_provider(mailbox_id, label, prov)
            seed_ids.add(mailbox_id)
    elif not legacy and mode == "gmail":
        from app.providers.gmail import GmailProvider

        def make_provider(mailbox_id: str) -> MailProvider:
            return GmailProvider(registry.vault(mailbox_id), client_secrets)

        for row in registry.list_mailboxes("gmail"):
            store.add_provider(row["id"], row["label"], make_provider(row["id"]))
    store.load_persisted()
    store.poll()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = None
        if (
            mode == "gmail" and not legacy
        ):  # el servidor consulta solo; no depende de la pestana

            async def _loop() -> None:
                while True:
                    await asyncio.sleep(POLL_SECONDS)
                    try:
                        await asyncio.to_thread(store.poll)
                    except Exception:
                        log.exception("Fallo la consulta periodica de correo")

            task = asyncio.create_task(_loop())
        yield
        if task:
            task.cancel()

    docs_on = os.environ.get("ATALAYA_DOCS") == "1"  # lista de rutas: solo si se pide a proposito
    app = FastAPI(
        title="Atalaya",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs" if docs_on else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_on else None,
    )

    def role_of(request: Request) -> str:
        """admin o supervisor. En la demo (sin cuentas) se elige con una cookie."""
        if admin:
            return admin.role(request) or "admin"
        if mode == "demo" and request.cookies.get(DEMO_ROLE_COOKIE) == "supervisor":
            return "supervisor"
        return "admin"

    @app.middleware("http")
    async def security(request: Request, call_next):
        path = request.url.path
        # CSRF: un formulario de otro sitio no puede enviar cabeceras personalizadas.
        if (
            request.method in WRITE_METHODS
            and path.startswith(("/api/", "/auth/"))
            and request.headers.get("x-requested-with") != "atalaya"
        ):
            return JSONResponse({"detail": "Solicitud no permitida."}, status_code=403)
        # Solo la persona administradora entra a la API (salvo lo publico de la invitacion).
        if (
            admin
            and path.startswith("/api/")
            and not path.startswith("/api/public/")
            and not admin.is_admin(request)
        ):
            return JSONResponse({"detail": "Inicia sesion."}, status_code=401)
        # El supervisor solo lee: se hace cumplir aqui, no solo ocultando botones.
        if (
            request.method in WRITE_METHODS
            and path.startswith("/api/")
            and path != "/api/demo/role"
            and role_of(request) == "supervisor"
        ):
            return JSONResponse(
                {"detail": "Tu rol es de solo lectura."}, status_code=403
            )
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if base_url.startswith("https"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if path.startswith(("/api/", "/auth/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # --- Paginas -------------------------------------------------------------------------
    @app.get("/", include_in_schema=False)
    def index(request: Request):
        if admin and not admin.is_admin(request):
            return RedirectResponse("/login")
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/login", include_in_schema=False)
    def login_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "login.html")

    @app.get("/invite/{token}", include_in_schema=False)
    def invite_page(token: str) -> FileResponse:
        return FileResponse(STATIC_DIR / "invite.html")

    @app.get("/connected", include_in_schema=False)
    def connected_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "connected.html")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "mode": mode, "auth": admin is not None}

    def actor_of(request: Request) -> str:
        """Quien hizo la accion (identidad enmascarada del administrador, o demo)."""
        return (admin.identity(request) if admin else None) or "admin-demo"

    # --- Alertas -------------------------------------------------------------------------
    def _alert_or_404(alert_id: str) -> Alert:
        alert = store.get(alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="Alerta no encontrada.")
        return alert

    @app.get("/api/alerts", response_model=list[Alert])
    def list_alerts(mailbox_id: str | None = None) -> list[Alert]:
        return store.list(mailbox_id)

    @app.get("/api/campaigns", response_model=list[campaigns.Campaign])
    def list_campaigns() -> list[campaigns.Campaign]:
        return campaigns.find_campaigns(store.list())

    @app.post("/api/campaigns/{campaign_id}/quarantine")
    def quarantine_campaign(
        campaign_id: str, request: Request, body: DecisionIn | None = None
    ) -> dict[str, int]:
        found = next(
            (c for c in campaigns.find_campaigns(store.list()) if c.id == campaign_id),
            None,
        )
        if found is None:
            raise HTTPException(status_code=404, detail="Campana no encontrada.")
        ids = [
            i
            for i in found.alert_ids
            if (alert := store.get(i)) and alert.status is not Status.quarantined
        ]
        if not ids:
            raise HTTPException(status_code=409, detail="Todo ya esta en cuarentena.")
        try:
            done, failed = store.approve_many(
                ids, actor_of(request), body.reason if body else None
            )
        except ReasonRequired as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        for alert in done:  # una entrada de auditoria por cada alerta, como la individual
            registry.audit(
                actor_of(request),
                "alert_quarantine",
                f"{alert.sender_domain} - {alert.mailbox_label or 'buzon'} (campana)",
            )
        if not done:
            raise HTTPException(
                status_code=502, detail="No se pudo completar la accion en el correo."
            )
        return {"quarantined": len(done), "failed": failed}

    @app.get("/api/alerts/{alert_id}", response_model=Alert)
    def get_alert(alert_id: str) -> Alert:
        return _alert_or_404(alert_id)

    def _act(
        fn, alert_id: str, request: Request, audit_action: str, body: DecisionIn | None
    ) -> Alert:
        _alert_or_404(alert_id)
        try:
            alert = fn(alert_id, actor_of(request), body.reason if body else None)
            registry.audit(
                actor_of(request),
                audit_action,
                f"{alert.sender_domain} - {alert.mailbox_label or 'buzon'}",
            )
            return alert
        except ReasonRequired as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:  # fallo del proveedor (token revocado, red, API)
            log.exception("Fallo la accion sobre el proveedor de correo")
            raise HTTPException(
                status_code=502, detail="No se pudo completar la accion en el correo."
            ) from exc

    @app.post("/api/alerts/{alert_id}/approve", response_model=Alert)
    def approve(
        alert_id: str, request: Request, body: DecisionIn | None = None
    ) -> Alert:
        return _act(store.approve, alert_id, request, "alert_quarantine", body)

    @app.post("/api/alerts/{alert_id}/reject", response_model=Alert)
    def reject(
        alert_id: str, request: Request, body: DecisionIn | None = None
    ) -> Alert:
        return _act(store.reject, alert_id, request, "alert_kept", body)

    @app.post("/api/alerts/{alert_id}/legit", response_model=Alert)
    def legit(alert_id: str, request: Request, body: DecisionIn | None = None) -> Alert:
        return _act(store.mark_legit, alert_id, request, "alert_legit", body)

    def _pdf_response(data: bytes, filename: str, download: bool) -> Response:
        disposition = "attachment" if download else "inline"
        return Response(
            data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"',
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get("/api/alerts/{alert_id}/report")
    def alert_report(
        alert_id: str, download: bool = False, formato: Literal["txt", "pdf"] = "txt"
    ) -> Response:
        alert = _alert_or_404(alert_id)
        if formato == "pdf":
            return _pdf_response(
                build_alert_pdf(alert, org_name), f"informe-{alert.id}.pdf", download
            )
        disposition = "attachment" if download else "inline"
        return PlainTextResponse(
            build_report(alert),
            headers={
                "Content-Disposition": f'{disposition}; filename="informe-{alert.id}.md"'
            },
        )

    @app.post("/api/poll")
    def poll() -> dict[str, int]:
        store.poll()
        return {"alerts": len(store.list())}

    # --- Buzones y cobertura ---------------------------------------------------------------
    status_cache: dict[str, tuple[float, object]] = {}

    def _status_of(mailbox_id: str, prov: MailProvider):
        """Con Gmail, comprobar la conexion es una llamada de red por buzon: con 200 buzones
        se guarda 60 s para que el panel siga rapido. La demo consulta siempre."""
        if mode != "gmail":
            return prov.connection_status()
        now = time.monotonic()
        hit = status_cache.get(mailbox_id)
        if hit and now - hit[0] < 60:
            return hit[1]
        status = prov.connection_status()
        status_cache[mailbox_id] = (now, status)
        return status

    @app.get("/api/coverage", response_model=list[Coverage])
    def coverage() -> list[Coverage]:
        rows = {m["id"]: m for m in registry.list_mailboxes()}
        result = []
        for mailbox_id, label, prov in store.providers():
            status = _status_of(mailbox_id, prov)  # primero: fija el nombre de la cuenta
            email = rows.get(mailbox_id, {}).get("email") or prov.account_name()
            result.append(
                Coverage(
                    mailbox_id=mailbox_id,
                    label=label or email,
                    account=email,
                    status=status,
                    last_check=store.last_check(mailbox_id),
                )
            )
        return result

    @app.delete("/api/mailboxes/{mailbox_id}")
    def disconnect_mailbox(mailbox_id: str, request: Request) -> dict[str, str]:
        row = registry.get_mailbox(mailbox_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Buzon no encontrado.")
        if row["kind"] == "gmail":
            token = registry.load_token(mailbox_id) or {}
            revoke_google_token(token.get("refresh_token") or token.get("token"))
        registry.delete_mailbox(mailbox_id, actor_of(request))
        store.remove_provider(mailbox_id)
        status_cache.pop(mailbox_id, None)
        return {"status": "disconnected"}

    # --- Invitaciones (solo administracion) --------------------------------------------------
    @app.post("/api/invites")
    def create_invite(body: InviteIn, request: Request) -> dict:
        if mode == "demo" and not legacy:  # tope por copia: la memoria de la demo es finita
            total = registry.db.query("SELECT COUNT(*) AS n FROM invites")[0]["n"]
            if total >= DEMO_MAX_INVITES:
                raise HTTPException(
                    status_code=409,
                    detail=f"La demo admite hasta {DEMO_MAX_INVITES} invitaciones; reinicia la demo.",
                )
        try:
            invite_id, token = registry.create_invite(body.label, actor_of(request))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        invite = next(i for i in registry.list_invites() if i["id"] == invite_id)
        return {
            "id": invite_id,
            "url": f"{base_url}/invite/{token}",
            "expires_at": invite["expires_at"],
        }

    @app.get("/api/invites")
    def list_invites() -> list[dict]:
        return registry.list_invites()

    @app.post("/api/invites/{invite_id}/revoke")
    def revoke_invite(invite_id: str, request: Request) -> dict[str, str]:
        if not registry.revoke_invite(invite_id, actor_of(request)):
            raise HTTPException(
                status_code=409, detail="La invitacion ya no se puede revocar."
            )
        return {"status": "revoked"}

    @app.get("/api/whoami")
    def whoami(request: Request) -> dict:
        return {"role": role_of(request), "demo_roles": admin is None and mode == "demo"}

    @app.post("/api/demo/role")
    def demo_role(body: DemoRoleIn) -> JSONResponse:
        """Solo demo: alterna entre administracion y supervisor para ensenar la vista de solo lectura."""
        if admin is not None or mode != "demo":
            raise HTTPException(status_code=404, detail="Solo disponible en modo demo.")
        response = JSONResponse({"role": body.role})
        response.set_cookie(
            DEMO_ROLE_COOKIE, body.role, httponly=True, samesite="lax", max_age=3600
        )
        return response

    @app.get("/api/org-report")
    def org_report(
        request: Request, download: bool = False, formato: Literal["txt", "pdf"] = "txt"
    ) -> Response:
        if formato == "pdf":
            alerts = store.list()
            return _pdf_response(
                build_org_pdf(
                    org_name,
                    alerts,
                    registry.list_audit(200),
                    campaigns.find_campaigns(alerts),
                    generated_by=actor_of(request),
                ),
                "informe-organizacion.pdf",
                download,
            )
        disposition = "attachment" if download else "inline"
        return PlainTextResponse(
            build_org_report(org_name, store.list(), registry.list_audit(200)),
            headers={
                "Content-Disposition": f'{disposition}; filename="reporte-organizacion.md"'
            },
        )

    @app.get("/api/audit")
    def audit() -> list[dict]:
        return registry.list_audit()

    # --- Demo ------------------------------------------------------------------------------
    @app.post("/api/demo/reset")
    def demo_reset(request: Request) -> dict[str, str]:
        if mode != "demo":
            raise HTTPException(status_code=404, detail="Solo disponible en modo demo.")
        for mailbox_id, _label, prov in store.providers():
            if mailbox_id in seed_ids or legacy:
                if isinstance(prov, DemoProvider):
                    prov.reset()
            else:  # buzones agregados por invitacion en esta demo
                registry.delete_mailbox(mailbox_id, actor_of(request))
                store.remove_provider(mailbox_id)
        if not legacy:  # tambien las invitaciones y el registro de esta copia (memoria acotada)
            registry.db.execute("DELETE FROM invites")
            registry.db.execute("DELETE FROM audit")
        store.clear()
        store.poll()
        return {"status": "reset"}

    # --- Rutas de conexion y de sesion --------------------------------------------------------
    ctx = AuthContext(
        registry=registry,
        store=store,
        mode=mode,
        org_name=org_name,
        admin=admin,
        client_secrets_file=secrets_file,
        client_secrets=client_secrets,
        make_provider=make_provider,
    )
    app.include_router(build_router(ctx))
    if admin:
        app.include_router(build_admin_router(admin, registry))
    return app


# Demo publica: una copia por visitante (ver app/demo_sessions.py). El modo gmail es una sola app.
if os.environ.get("ATALAYA_MODE", "demo") == "demo":
    from app.demo_sessions import DemoSessions

    app = DemoSessions(create_app)
else:
    app = create_app()

"""API de Atalaya.

Modos (variable ATALAYA_MODE):
- demo  (por defecto): bandeja simulada, sin cuentas reales. Es el unico modo publico.
- gmail: conexion real con Gmail; solo uso local con usuarios de prueba.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.models import Alert, Coverage
from app.providers.base import MailProvider
from app.providers.demo import DemoProvider
from app.store import AlertStore

load_dotenv()
log = logging.getLogger("atalaya")

STATIC_DIR = Path(__file__).parent / "static"
ADMIN = "admin-demo"  # en modo conectado vendra de la sesion autenticada


def create_app(provider: MailProvider | None = None) -> FastAPI:
    mode = os.environ.get("ATALAYA_MODE", "demo")
    gmail_setup = None
    if provider is None:
        if mode == "demo":
            provider = DemoProvider()
        elif mode == "gmail":
            from app.providers.gmail import GmailProvider, load_client_secrets
            from app.tokens import TokenVault

            secrets_file = os.environ["GOOGLE_CLIENT_SECRETS_FILE"]
            vault = TokenVault(
                os.environ.get("ATALAYA_TOKEN_PATH", "data/token.enc"),
                os.environ["ATALAYA_FERNET_KEY"],
            )
            provider = GmailProvider(vault, load_client_secrets(secrets_file))
            gmail_setup = secrets_file
        else:
            raise RuntimeError("ATALAYA_MODE debe ser 'demo' o 'gmail'.")

    store = AlertStore(provider)
    store.poll()

    app = FastAPI(title="Atalaya", version="0.1.0")

    @app.middleware("http")
    async def security(request: Request, call_next):
        # CSRF: un formulario de otro sitio no puede enviar cabeceras personalizadas.
        if (
            request.method == "POST"
            and request.url.path.startswith(("/api/", "/auth/"))
            and request.headers.get("x-requested-with") != "atalaya"
        ):
            return JSONResponse({"detail": "Solicitud no permitida."}, status_code=403)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    def _alert_or_404(alert_id: str) -> Alert:
        alert = store.get(alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="Alerta no encontrada.")
        return alert

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": mode}

    @app.get("/api/alerts", response_model=list[Alert])
    def list_alerts() -> list[Alert]:
        return store.list()

    @app.get("/api/alerts/{alert_id}", response_model=Alert)
    def get_alert(alert_id: str) -> Alert:
        return _alert_or_404(alert_id)

    def _act(fn, alert_id: str) -> Alert:
        _alert_or_404(alert_id)
        try:
            return fn(alert_id, ADMIN)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:  # fallo del proveedor (token revocado, red, API)
            log.exception("Fallo la accion sobre el proveedor de correo")
            raise HTTPException(
                status_code=502, detail="No se pudo completar la accion en el correo."
            ) from exc

    @app.post("/api/alerts/{alert_id}/approve", response_model=Alert)
    def approve(alert_id: str) -> Alert:
        return _act(store.approve, alert_id)

    @app.post("/api/alerts/{alert_id}/reject", response_model=Alert)
    def reject(alert_id: str) -> Alert:
        return _act(store.reject, alert_id)

    @app.post("/api/alerts/{alert_id}/legit", response_model=Alert)
    def legit(alert_id: str) -> Alert:
        return _act(store.mark_legit, alert_id)

    @app.post("/api/poll")
    def poll() -> dict[str, int]:
        store.poll()
        return {"alerts": len(store.list())}

    @app.get("/api/coverage", response_model=list[Coverage])
    def coverage() -> list[Coverage]:
        return [
            Coverage(
                account=provider.account_name(), status=provider.connection_status()
            )
        ]

    @app.post("/api/demo/reset")
    def demo_reset() -> dict[str, str]:
        if not isinstance(provider, DemoProvider):
            raise HTTPException(status_code=404, detail="Solo disponible en modo demo.")
        provider.reset()
        store.clear()
        store.poll()
        return {"status": "reset"}

    if gmail_setup:
        from app.auth import build_router

        app.include_router(build_router(provider, gmail_setup, store.poll))

    return app


app = create_app()

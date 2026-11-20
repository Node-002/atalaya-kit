"""Login con Google (solo modo 'gmail', uso local con usuarios de prueba).

Proteccion del flujo: `state` aleatorio ligado a una cookie HttpOnly del navegador
que inicio el login (evita login CSRF) y PKCE (code_verifier guardado en el servidor).
"""

import logging
import os
import secrets
import time
from collections.abc import Callable
from pathlib import Path

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow

from app.providers.gmail import SCOPES, GmailProvider

log = logging.getLogger("atalaya.auth")

REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
)
STATE_COOKIE = "atalaya_oauth_state"
STATE_TTL = 600  # segundos

# oauthlib exige https; solo se relaja para localhost en desarrollo.
if REDIRECT_URI.startswith("http://localhost"):
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")


def build_router(
    provider: GmailProvider,
    client_secrets_file: str | Path,
    on_connected: Callable[[], None],
) -> APIRouter:
    router = APIRouter()
    pending: dict[str, tuple[str, float]] = {}  # state -> (code_verifier, creado)

    def _flow() -> Flow:
        return Flow.from_client_secrets_file(
            str(client_secrets_file), scopes=SCOPES, redirect_uri=REDIRECT_URI
        )

    def _purge() -> None:
        now = time.time()
        for key in [k for k, (_, t) in pending.items() if now - t > STATE_TTL]:
            pending.pop(key, None)

    @router.get("/auth/google/login")
    def login() -> RedirectResponse:
        _purge()
        flow = _flow()
        state = secrets.token_urlsafe(32)
        flow.code_verifier = secrets.token_urlsafe(64)
        url, _ = flow.authorization_url(
            state=state,
            access_type="offline",
            prompt="consent",
            include_granted_scopes="false",
        )
        pending[state] = (flow.code_verifier, time.time())
        response = RedirectResponse(url)
        response.set_cookie(
            STATE_COOKIE,
            state,
            max_age=STATE_TTL,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return response

    @router.get("/auth/google/callback")
    def callback(
        request: Request,
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
    ):
        _purge()
        if error:
            return RedirectResponse("/?auth=cancelado")
        cookie_state = request.cookies.get(STATE_COOKIE)
        if not code or not state or state != cookie_state or state not in pending:
            raise HTTPException(
                status_code=400, detail="Solicitud de inicio de sesion no valida."
            )
        verifier, _ = pending.pop(state)
        flow = _flow()
        flow.code_verifier = verifier
        flow.fetch_token(code=code)
        creds = flow.credentials
        if not creds.refresh_token:
            raise HTTPException(
                status_code=400, detail="Google no entrego permiso de acceso continuo."
            )
        provider.vault.save(
            {"token": creds.token, "refresh_token": creds.refresh_token}
        )
        provider.reset_cache()
        on_connected()
        response = RedirectResponse("/?auth=ok")
        response.delete_cookie(STATE_COOKIE)
        return response

    @router.post("/auth/disconnect")
    def disconnect() -> JSONResponse:
        data = provider.vault.load()
        if data:
            token = data.get("refresh_token") or data.get("token")
            try:
                requests.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": token},
                    timeout=10,
                )
            except requests.RequestException:
                log.warning(
                    "No se pudo revocar el token en Google; se borra solo el local."
                )
        provider.vault.delete()
        provider.reset_cache()
        return JSONResponse({"status": "disconnected"})

    return router

"""Conexion de buzones: invitacion -> consentimiento -> Google (ver docs/adr/0003).

Quien usa el panel (administracion) y quien tiene el correo son personas distintas:
la administracion crea un enlace de un solo uso; la persona dueña del buzon lo abre,
lee el consentimiento, autoriza con Google (sin compartir contrasena) y ve solo una
confirmacion. No ve alertas ni panel.

Proteccion del flujo de Google: `state` aleatorio ligado a una cookie HttpOnly del
navegador que lo inicio (evita login CSRF) y PKCE (code_verifier en el servidor).
"""

import logging
import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.admin import AdminAuth
from app.identity import is_safe_email, normalize_email
from app.providers.base import MailProvider
from app.providers.demo import new_demo_employee
from app.registry import Registry
from app.store import AlertStore

log = logging.getLogger("atalaya.auth")

REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
)
STATE_COOKIE = "atalaya_oauth_state"
STATE_TTL = 600  # segundos
INVALID_INVITE = (
    "Este enlace no es valido o ya vencio. Pide uno nuevo a quien te lo envio."
)

# oauthlib exige https; solo se relaja para localhost en desarrollo.
if REDIRECT_URI.startswith("http://localhost"):
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")


@dataclass
class AuthContext:
    registry: Registry
    store: AlertStore
    mode: str
    org_name: str
    admin: AdminAuth | None = None
    client_secrets_file: str | None = None
    client_secrets: dict | None = None
    make_provider: Callable[[str], MailProvider] | None = None
    pending: dict = field(
        default_factory=dict
    )  # state -> (code_verifier, creado, invite_id)


def revoke_google_token(token: str | None) -> None:
    if not token:
        return
    try:
        requests.post(
            "https://oauth2.googleapis.com/revoke", params={"token": token}, timeout=10
        )
    except requests.RequestException:
        log.warning("No se pudo revocar el token en Google; se borra solo el local.")


def build_router(ctx: AuthContext) -> APIRouter:
    router = APIRouter()
    registry, store = ctx.registry, ctx.store

    def _pending_invite(token: str | None) -> dict:
        row = registry.find_invite(token) if token else None
        if row is None or row["status"] != "pending":
            raise HTTPException(status_code=410, detail=INVALID_INVITE)
        return row

    @router.get("/api/public/invite/{token}")
    def invite_info(token: str) -> dict:
        row = registry.find_invite(token)
        valid = bool(row and row["status"] == "pending")
        return {
            "valid": valid,
            "label": row["label"] if valid else None,
            "org": ctx.org_name,
            "mode": ctx.mode,
        }

    def _purge() -> None:
        now = time.time()
        for key in [k for k, v in ctx.pending.items() if now - v[1] > STATE_TTL]:
            ctx.pending.pop(key, None)

    # --- Google (modo gmail) -------------------------------------------------------------
    if ctx.mode == "gmail":
        from google_auth_oauthlib.flow import Flow

        from app.providers.gmail import SCOPES, fetch_email

        def _flow() -> Flow:
            return Flow.from_client_secrets_file(
                str(ctx.client_secrets_file), scopes=SCOPES, redirect_uri=REDIRECT_URI
            )

        @router.get("/auth/google/login")
        def login(
            request: Request, invite: str | None = None, consent: str | None = None
        ):
            _purge()
            invite_id = None
            if invite:
                row = _pending_invite(invite)
                if consent != "1":
                    raise HTTPException(
                        status_code=400, detail="Debes aceptar el consentimiento."
                    )
                invite_id = row["id"]
            elif not (ctx.admin and ctx.admin.is_admin(request)):
                raise HTTPException(
                    status_code=401, detail="Inicia sesion como administrador."
                )
            flow = _flow()
            state = secrets.token_urlsafe(32)
            flow.code_verifier = secrets.token_urlsafe(64)
            url, _ = flow.authorization_url(
                state=state,
                access_type="offline",
                prompt="consent",
                include_granted_scopes="false",
            )
            ctx.pending[state] = (flow.code_verifier, time.time(), invite_id)
            response = RedirectResponse(url)
            response.set_cookie(
                STATE_COOKIE,
                state,
                max_age=STATE_TTL,
                httponly=True,
                samesite="lax",
                secure=REDIRECT_URI.startswith("https"),
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
                return RedirectResponse("/connected?result=cancelado")
            cookie_state = request.cookies.get(STATE_COOKIE)
            if (
                not code
                or not state
                or state != cookie_state
                or state not in ctx.pending
            ):
                raise HTTPException(
                    status_code=400, detail="Solicitud de inicio de sesion no valida."
                )
            verifier, _, invite_id = ctx.pending.pop(state)
            flow = _flow()
            flow.code_verifier = verifier
            try:
                flow.fetch_token(code=code)
                creds = flow.credentials
                email = fetch_email(creds)
            except Exception as exc:
                log.warning("Fallo el intercambio con Google: %s", type(exc).__name__)
                raise HTTPException(
                    status_code=400, detail="No se pudo completar la conexion."
                ) from exc
            if not creds.refresh_token:
                raise HTTPException(
                    status_code=400,
                    detail="Google no entrego permiso de acceso continuo.",
                )

            if not is_safe_email(email):
                # Letras de otro alfabeto, acentos o punycode: posible suplantacion.
                revoke_google_token(creds.refresh_token)
                registry.audit("sistema", "mailbox_rejected_identity", ascii(email))
                raise HTTPException(
                    status_code=400,
                    detail="Esa direccion usa caracteres no permitidos y no se puede conectar.",
                )
            email = normalize_email(email)
            existing = registry.find_mailbox_by_email(email)
            label = "Administracion"
            if invite_id:
                label = next(
                    (
                        i["label"]
                        for i in registry.list_invites()
                        if i["id"] == invite_id
                    ),
                    email,
                )
            mailbox_id = registry.add_mailbox(
                label,
                email,
                "gmail",
                invite_id,
                consent=bool(invite_id),
                token={"token": creds.token, "refresh_token": creds.refresh_token},
            )
            if invite_id and not registry.consume_invite(invite_id, mailbox_id):
                # La invitacion se revoco o vencio durante el proceso: no se conserva el acceso.
                if existing is None:
                    registry.delete_mailbox(mailbox_id, "sistema")
                    revoke_google_token(creds.refresh_token)
                raise HTTPException(status_code=410, detail=INVALID_INVITE)

            if store.has_provider(mailbox_id):
                for mid, _label, prov in store.providers():
                    if mid == mailbox_id and hasattr(prov, "reset_cache"):
                        prov.reset_cache()
            elif ctx.make_provider:
                store.add_provider(mailbox_id, label, ctx.make_provider(mailbox_id))
            store.poll()
            response = RedirectResponse("/connected?result=ok" if invite_id else "/")
            response.delete_cookie(STATE_COOKIE)
            return response

    # --- Demo: la misma invitacion, con un buzon simulado --------------------------------
    if ctx.mode == "demo":

        @router.get("/auth/demo/connect")
        def demo_connect(invite: str | None = None, consent: str | None = None):
            row = _pending_invite(invite)
            if consent != "1":
                raise HTTPException(
                    status_code=400, detail="Debes aceptar el consentimiento."
                )
            slug = "nuevo-" + secrets.token_hex(2)
            provider = new_demo_employee(row["label"], slug)
            mailbox_id = registry.add_mailbox(
                row["label"], provider.account_name(), "demo", row["id"], consent=True
            )
            if not registry.consume_invite(row["id"], mailbox_id):
                registry.delete_mailbox(mailbox_id, "sistema")
                raise HTTPException(status_code=410, detail=INVALID_INVITE)
            store.add_provider(mailbox_id, row["label"], provider)
            store.poll()
            return RedirectResponse("/connected?result=ok")

    return router

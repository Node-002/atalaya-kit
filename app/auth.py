"""Conexion con Google: (1) buzones por invitacion y (2) acceso de la administracion.

(1) Quien usa el panel y quien tiene el correo son personas distintas: la administracion
crea un enlace de un solo uso; la persona duena del buzon lo abre, lee el consentimiento,
autoriza con Google (sin compartir contrasena) y ve solo una confirmacion. No ve el panel.

(2) La administracion puede entrar con su cuenta de Google (solo cuentas autorizadas).

Proteccion del flujo: `state` aleatorio ligado a una cookie HttpOnly del navegador que lo
inicio (evita login CSRF), PKCE, y `nonce` verificado en el token de identidad.
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
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.admin import AdminAuth, set_session_cookie
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
# Diferencia de reloj tolerada al verificar el token de identidad. Con 0 (el valor por defecto
# de la libreria) basta que el reloj local vaya 1 s atrasado para rechazar un token valido.
CLOCK_SKEW_SECONDS = 30
ADMIN_SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email"]
INVALID_INVITE = (
    "Este enlace no es valido o ya vencio. Pide uno nuevo a quien te lo envio."
)
LOGIN_ERROR = "/login?error=1"  # mensaje generico: no revela por que se nego

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
    pending: dict = field(default_factory=dict)  # state -> datos del intento en curso


def revoke_google_token(token: str | None) -> None:
    if not token:
        return
    try:
        requests.post(
            "https://oauth2.googleapis.com/revoke", params={"token": token}, timeout=10
        )
    except requests.RequestException:
        log.warning("No se pudo revocar el token en Google; se borra solo el local.")


def _verify_identity_token(token: str, audience: str) -> dict:
    """Verifica firma, emisor, destinatario y vencimiento del token de identidad de Google."""
    return google_id_token.verify_oauth2_token(
        token,
        google_requests.Request(),
        audience,
        clock_skew_in_seconds=CLOCK_SKEW_SECONDS,
    )


def _google_admin_claims(ctx: AuthContext, code: str, verifier: str) -> dict:
    """Intercambia el codigo y VERIFICA el token de identidad. Funcion de modulo para poder
    sustituirla en pruebas sin red."""
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(
        str(ctx.client_secrets_file), scopes=ADMIN_SCOPES, redirect_uri=REDIRECT_URI
    )
    flow.code_verifier = verifier
    flow.fetch_token(code=code)
    return _verify_identity_token(
        flow.credentials.id_token, ctx.client_secrets["web"]["client_id"]
    )


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
        for key in [
            k for k, v in ctx.pending.items() if now - v["created"] > STATE_TTL
        ]:
            ctx.pending.pop(key, None)

    # --- Google (modo gmail) -------------------------------------------------------------
    if ctx.mode == "gmail":
        from google_auth_oauthlib.flow import Flow

        from app.providers.gmail import SCOPES, fetch_email

        def _flow(scopes: list[str]) -> Flow:
            return Flow.from_client_secrets_file(
                str(ctx.client_secrets_file), scopes=scopes, redirect_uri=REDIRECT_URI
            )

        def _start(scopes: list[str], entry: dict, **extra) -> RedirectResponse:
            _purge()
            flow = _flow(scopes)
            state = secrets.token_urlsafe(32)
            verifier = secrets.token_urlsafe(64)
            flow.code_verifier = verifier
            url, _ = flow.authorization_url(
                state=state, include_granted_scopes="false", **extra
            )
            ctx.pending[state] = {**entry, "verifier": verifier, "created": time.time()}
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

        # (2) Acceso de la administracion con Google ---------------------------------------
        @router.get("/auth/admin/google/login")
        def admin_google_login(request: Request):
            if not (ctx.admin and ctx.admin.google_enabled):
                raise HTTPException(status_code=404, detail="No disponible.")
            wait = ctx.admin.retry_after(ctx.admin.client_ip(request))
            if wait:
                raise HTTPException(
                    status_code=429,
                    detail="Demasiados intentos. Intenta mas tarde.",
                    headers={"Retry-After": str(wait)},
                )
            nonce = secrets.token_urlsafe(16)
            extra = {
                "access_type": "online",
                "prompt": "select_account",
                "nonce": nonce,
            }
            if ctx.admin.domain:
                extra["hd"] = (
                    ctx.admin.domain
                )  # pista para Google; se vuelve a verificar aqui
            return _start(ADMIN_SCOPES, {"purpose": "admin", "nonce": nonce}, **extra)

        def _admin_callback(
            request: Request, code: str, entry: dict
        ) -> RedirectResponse:
            admin = ctx.admin
            client = admin.client_ip(request)
            if admin.retry_after(client):
                return RedirectResponse(LOGIN_ERROR)
            try:
                claims = _google_admin_claims(ctx, code, entry["verifier"])
            except Exception as exc:  # noqa: BLE001  cualquier fallo del intercambio es un fallo de acceso
                log.warning(
                    "Fallo el acceso de administracion con Google: %s (%s)",
                    type(exc).__name__,
                    str(exc)[:160],
                )
                admin.record_failure(client)
                time.sleep(admin.failure_delay)
                return RedirectResponse(LOGIN_ERROR)
            identity = admin.authorize_google(claims, entry["nonce"])
            if identity is None:
                admin.record_denied_google(client, claims)
                time.sleep(admin.failure_delay)
                return RedirectResponse(
                    LOGIN_ERROR
                )  # mismo mensaje que cualquier otro fallo
            admin.record_success(client, identity)
            response = RedirectResponse("/")
            set_session_cookie(response, admin, admin.new_session(identity))
            response.delete_cookie(STATE_COOKIE)
            return response

        # (1) Conexion de buzones --------------------------------------------------------
        @router.get("/auth/google/login")
        def login(
            request: Request, invite: str | None = None, consent: str | None = None
        ):
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
            return _start(
                SCOPES,
                {"purpose": "mailbox", "invite_id": invite_id},
                access_type="offline",
                prompt="consent",
            )

        @router.get("/auth/google/callback")
        def callback(
            request: Request,
            code: str | None = None,
            state: str | None = None,
            error: str | None = None,
        ):
            _purge()
            entry = ctx.pending.get(state) if state else None
            if error:
                ctx.pending.pop(state, None) if state else None
                if entry and entry["purpose"] == "admin":
                    return RedirectResponse(LOGIN_ERROR)
                return RedirectResponse("/connected?result=cancelado")
            cookie_state = request.cookies.get(STATE_COOKIE)
            if not code or not state or state != cookie_state or entry is None:
                raise HTTPException(
                    status_code=400, detail="Solicitud de inicio de sesion no valida."
                )
            ctx.pending.pop(state)
            if entry["purpose"] == "admin":
                return _admin_callback(request, code, entry)

            invite_id = entry["invite_id"]
            flow = _flow(SCOPES)
            flow.code_verifier = entry["verifier"]
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

"""Acceso de la administracion (quienes usan el panel de Atalaya).

Dos formas, configurables por variables de entorno (al menos una es obligatoria):
- Google (recomendada): solo entran las cuentas de ATALAYA_ADMIN_EMAILS. Atalaya no
  guarda contrasenas de administradores; Google se ocupa de la contrasena y del 2.o factor.
- Contrasena (respaldo): ATALAYA_ADMIN_PASSWORD, minimo 12 caracteres.

Defensas: bloqueo progresivo y persistente por direccion, retraso en cada fallo, avisos a
otras personas, sesiones que se pueden invalidar, y NUNCA se expone la lista de cuentas
autorizadas (los errores son genericos y las cuentas se muestran enmascaradas).
"""

import asyncio
import hashlib
import hmac
import secrets
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.alerts import SecurityNotifier
from app.identity import is_safe_email, mask_email, normalize_email
from app.ratelimit import MAX_FAILURES, RateLimiter
from app.registry import Registry

COOKIE = "atalaya_session"
SESSION_SECONDS = 8 * 3600
MIN_PASSWORD_LENGTH = 12
GLOBAL_WINDOW = timedelta(hours=1)
GLOBAL_THRESHOLD = 20
FAILURE_ACTIONS = ("admin_login_failed", "admin_login_denied")
GENERIC_DENIAL = "No se pudo iniciar sesion."


class AdminAuth:
    def __init__(
        self,
        secret: str,
        registry: Registry,
        *,
        password: str | None = None,
        emails: frozenset[str] = frozenset(),
        domain: str | None = None,
        secure_cookie: bool = False,
        limiter: RateLimiter | None = None,
        notifier: SecurityNotifier | None = None,
        failure_delay: float = 0.4,
        trust_proxy: bool = False,
    ) -> None:
        if len(secret) < 32:
            raise RuntimeError(
                "ATALAYA_SESSION_SECRET debe tener al menos 32 caracteres."
            )
        if password is not None and len(password) < MIN_PASSWORD_LENGTH:
            raise RuntimeError(
                f"ATALAYA_ADMIN_PASSWORD debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
            )
        if password is None and not emails:
            raise RuntimeError(
                "Configura ATALAYA_ADMIN_EMAILS (inicio de sesion con Google) "
                "y/o ATALAYA_ADMIN_PASSWORD."
            )
        self._secret = secret
        self._password_hash = (
            hashlib.sha256(password.encode()).digest() if password else None
        )
        self._emails = emails
        self._domain = domain.lower() if domain else None
        self.secure_cookie = secure_cookie
        self.registry = registry
        self.limiter = limiter or RateLimiter(registry.db)
        self.notifier = notifier
        self.failure_delay = failure_delay
        self.trust_proxy = trust_proxy
        self._sessions: dict[
            str, tuple[float, str]
        ] = {}  # sid -> (vencimiento, identidad)

    # --- Que formas de acceso hay ----------------------------------------------------------
    @property
    def password_enabled(self) -> bool:
        return self._password_hash is not None

    @property
    def google_enabled(self) -> bool:
        return bool(self._emails)

    @property
    def domain(self) -> str | None:
        return self._domain

    # --- Contrasena (respaldo) ------------------------------------------------------------
    def check_password(self, candidate: str) -> bool:
        if self._password_hash is None:
            return False
        return hmac.compare_digest(
            hashlib.sha256(candidate.encode()).digest(), self._password_hash
        )

    # --- Google ----------------------------------------------------------------------------
    def _identity(self, email: str) -> str:
        """Etiqueta estable y enmascarada: ma***@dominio#a1b2 (no revela la cuenta)."""
        tag = hmac.new(
            self._secret.encode(), email.encode(), hashlib.sha256
        ).hexdigest()[:4]
        return f"{mask_email(email)}#{tag}"

    def authorize_google(self, claims: dict, nonce: str) -> str | None:
        """Devuelve la identidad enmascarada si la cuenta esta autorizada; si no, None.
        Verifica correo confirmado, nonce, lista de cuentas, regla ASCII y dominio."""
        email = claims.get("email")
        if claims.get("email_verified") is not True or not isinstance(email, str):
            return None
        if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
            return None
        email = normalize_email(email)
        if not is_safe_email(email) or email not in self._emails:
            return None
        if self._domain and str(claims.get("hd", "")).lower() != self._domain:
            return None
        return self._identity(email)

    def masked_account(self, claims: dict) -> str:
        email = claims.get("email")
        if isinstance(email, str) and is_safe_email(normalize_email(email)):
            return mask_email(normalize_email(email))
        return "(cuenta no valida)"

    # --- Sesiones (se pueden invalidar en el servidor) -----------------------------------
    def new_session(self, identity: str) -> str:
        now = time.monotonic()
        for sid in [k for k, (exp, _) in self._sessions.items() if exp < now]:
            self._sessions.pop(sid, None)
        sid = secrets.token_urlsafe(24)
        self._sessions[sid] = (now + SESSION_SECONDS, identity)
        return sid  # la cookie lleva solo este identificador: ningun dato personal

    def _session(self, request: Request) -> tuple[str, str] | None:
        sid = request.cookies.get(COOKIE)
        entry = self._sessions.get(sid) if sid else None
        if entry is None or entry[0] < time.monotonic():
            return None
        return sid, entry[1]

    def is_admin(self, request: Request) -> bool:
        return self._session(request) is not None

    def identity(self, request: Request) -> str | None:
        session = self._session(request)
        return session[1] if session else None

    def end_session(self, request: Request) -> None:
        session = self._session(request)
        if session:
            self._sessions.pop(session[0], None)

    # --- Intentos de acceso ----------------------------------------------------------------
    def client_ip(self, request: Request) -> str:
        if (
            self.trust_proxy
        ):  # solo detras de un proxy propio: toma la ultima direccion que anadio
            forwarded = request.headers.get("x-forwarded-for", "")
            if forwarded:
                return forwarded.split(",")[-1].strip()
        return request.client.host if request.client else "?"

    def retry_after(self, client: str) -> int:
        return self.limiter.retry_after(client)

    def record_success(self, client: str, actor: str) -> None:
        self.limiter.register_success(client)
        self.registry.audit(actor, "admin_login", client)

    def record_failure(self, client: str, action: str = "admin_login_failed") -> None:
        self.registry.audit("desconocido", action, client)
        event = self.limiter.register_failure(client)
        if self.notifier is None:
            return
        if event:
            self.notifier.notify(
                "bloqueo",
                f"La direccion {client} quedo bloqueada hasta {event.until:%H:%M} UTC "
                f"tras {MAX_FAILURES} intentos fallidos (reincidencia nivel {event.level}).",
            )
        recent = self.registry.count_audit(
            FAILURE_ACTIONS, datetime.now(UTC) - GLOBAL_WINDOW
        )
        if recent >= GLOBAL_THRESHOLD:
            self.notifier.notify(
                "ataque_distribuido",
                f"{recent} intentos de acceso fallidos en la ultima hora.",
            )

    def record_denied_google(self, client: str, claims: dict) -> None:
        """Una cuenta de Google que NO esta autorizada intento entrar."""
        self.record_failure(client, "admin_login_denied")
        if self.notifier:
            self.notifier.notify(
                "acceso_denegado",
                f"La cuenta {self.masked_account(claims)} intento entrar desde {client}.",
            )


def build_admin_router(admin: AdminAuth, registry: Registry) -> APIRouter:
    router = APIRouter()

    @router.get("/api/public/login-options")
    def options() -> dict[str, bool]:
        return {"google": admin.google_enabled, "password": admin.password_enabled}

    @router.post("/auth/admin/login")
    async def login(request: Request) -> JSONResponse:
        if not admin.password_enabled:
            raise HTTPException(status_code=404, detail="No disponible.")
        client = admin.client_ip(request)
        wait = admin.retry_after(client)
        if wait:
            registry.audit("desconocido", "admin_login_blocked", client)
            raise HTTPException(
                status_code=429,
                detail="Demasiados intentos. Intenta mas tarde.",
                headers={"Retry-After": str(wait)},
            )
        try:
            body = await request.json()
        except ValueError:
            body = {}
        password = body.get("password") if isinstance(body, dict) else None
        if not isinstance(password, str) or not admin.check_password(password):
            admin.record_failure(client)
            await asyncio.sleep(admin.failure_delay)
            raise HTTPException(status_code=401, detail="Contrasena incorrecta.")
        admin.record_success(client, "administracion")
        response = JSONResponse({"status": "ok"})
        set_session_cookie(
            response, admin, admin.new_session("administracion (contrasena)")
        )
        return response

    @router.post("/auth/admin/logout")
    def logout(request: Request) -> JSONResponse:
        admin.end_session(request)
        response = JSONResponse({"status": "ok"})
        response.delete_cookie(COOKIE)
        return response

    @router.get("/api/me")
    def me(request: Request) -> dict[str, str]:
        identity = admin.identity(request)
        if identity is None:
            raise HTTPException(status_code=401, detail="Inicia sesion.")
        return {"role": "admin", "id": identity}

    @router.get("/api/security/events")
    def security_events() -> list[dict]:
        return registry.list_security_events()

    return router


def set_session_cookie(response: JSONResponse, admin: AdminAuth, sid: str) -> None:
    response.set_cookie(
        COOKIE,
        sid,
        max_age=SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=admin.secure_cookie,
    )

"""Login de la persona administradora (quien usa el panel de Atalaya).

- Contrasena en una variable de entorno (minimo 12 caracteres); sin ella, el modo
  conectado NO arranca.
- Sesion en cookie firmada (HttpOnly, SameSite=Lax, vence en 8 h).
- Limite de intentos fallidos por direccion (5 cada 5 minutos).
"""

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.registry import Registry

COOKIE = "atalaya_session"
SESSION_SECONDS = 8 * 3600
MAX_FAILURES = 5
WINDOW_SECONDS = 300
MIN_PASSWORD_LENGTH = 12


class AdminAuth:
    def __init__(self, password: str, secret: str, secure_cookie: bool = False) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise RuntimeError(
                f"ATALAYA_ADMIN_PASSWORD debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
            )
        if len(secret) < 32:
            raise RuntimeError(
                "ATALAYA_SESSION_SECRET debe tener al menos 32 caracteres."
            )
        self._password_hash = hashlib.sha256(password.encode()).digest()
        self._serializer = URLSafeTimedSerializer(secret, salt="atalaya-admin")
        self.secure_cookie = secure_cookie
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._sessions: dict[
            str, float
        ] = {}  # sid -> vencimiento; permite cerrar sesion de verdad

    def check_password(self, candidate: str) -> bool:
        return hmac.compare_digest(
            hashlib.sha256(candidate.encode()).digest(), self._password_hash
        )

    def new_session(self) -> str:
        now = time.monotonic()
        for sid in [k for k, exp in self._sessions.items() if exp < now]:
            self._sessions.pop(sid, None)
        sid = secrets.token_urlsafe(16)
        self._sessions[sid] = now + SESSION_SECONDS
        return self._serializer.dumps({"role": "admin", "sid": sid})

    def _session_id(self, request: Request) -> str | None:
        token = request.cookies.get(COOKIE)
        if not token:
            return None
        try:
            data = self._serializer.loads(token, max_age=SESSION_SECONDS)
        except (BadSignature, SignatureExpired):
            return None
        if data.get("role") != "admin":
            return None
        sid = data.get("sid")
        return (
            sid
            if isinstance(sid, str) and self._sessions.get(sid, 0) > time.monotonic()
            else None
        )

    def is_admin(self, request: Request) -> bool:
        return self._session_id(request) is not None

    def end_session(self, request: Request) -> None:
        """Invalida la sesion en el servidor: una cookie copiada ya no sirve."""
        sid = self._session_id(request)
        if sid:
            self._sessions.pop(sid, None)

    # --- limite de intentos -----------------------------------------------------------
    def _recent(self, client: str) -> deque[float]:
        window = self._failures[client]
        cutoff = time.monotonic() - WINDOW_SECONDS
        while window and window[0] < cutoff:
            window.popleft()
        return window

    def locked_out(self, client: str) -> bool:
        return len(self._recent(client)) >= MAX_FAILURES

    def register_failure(self, client: str) -> None:
        self._recent(client).append(time.monotonic())


def build_admin_router(admin: AdminAuth, registry: Registry) -> APIRouter:
    router = APIRouter()

    @router.post("/auth/admin/login")
    async def login(request: Request) -> JSONResponse:
        client = request.client.host if request.client else "?"
        if admin.locked_out(client):
            registry.audit("desconocido", "admin_login_blocked", client)
            raise HTTPException(
                status_code=429, detail="Demasiados intentos. Espera unos minutos."
            )
        try:
            body = await request.json()
        except ValueError:
            body = {}
        password = body.get("password") if isinstance(body, dict) else None
        if not isinstance(password, str) or not admin.check_password(password):
            admin.register_failure(client)
            registry.audit("desconocido", "admin_login_failed", client)
            raise HTTPException(status_code=401, detail="Contrasena incorrecta.")
        response = JSONResponse({"status": "ok"})
        response.set_cookie(
            COOKIE,
            admin.new_session(),
            max_age=SESSION_SECONDS,
            httponly=True,
            samesite="lax",
            secure=admin.secure_cookie,
        )
        registry.audit("administrador", "admin_login", client)
        return response

    @router.post("/auth/admin/logout")
    def logout(request: Request) -> JSONResponse:
        admin.end_session(request)
        response = JSONResponse({"status": "ok"})
        response.delete_cookie(COOKIE)
        return response

    @router.get("/api/me")
    def me(request: Request) -> dict[str, str]:
        if not admin.is_admin(request):
            raise HTTPException(status_code=401, detail="Inicia sesion.")
        return {"role": "admin"}

    return router

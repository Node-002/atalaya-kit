"""Login de la persona administradora (quien usa el panel de Atalaya).

- Contrasena en una variable de entorno (minimo 12 caracteres); sin ella, el modo
  conectado NO arranca.
- Sesion en cookie firmada (HttpOnly, SameSite=Lax, vence en 8 h).
- Limite de intentos fallidos por direccion (5 cada 5 minutos).
"""

import hashlib
import hmac
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

    def check_password(self, candidate: str) -> bool:
        return hmac.compare_digest(
            hashlib.sha256(candidate.encode()).digest(), self._password_hash
        )

    def new_session(self) -> str:
        return self._serializer.dumps({"role": "admin"})

    def is_admin(self, request: Request) -> bool:
        token = request.cookies.get(COOKIE)
        if not token:
            return False
        try:
            data = self._serializer.loads(token, max_age=SESSION_SECONDS)
        except (BadSignature, SignatureExpired):
            return False
        return data.get("role") == "admin"

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
    def logout() -> JSONResponse:
        response = JSONResponse({"status": "ok"})
        response.delete_cookie(COOKIE)
        return response

    @router.get("/api/me")
    def me(request: Request) -> dict[str, str]:
        if not admin.is_admin(request):
            raise HTTPException(status_code=401, detail="Inicia sesion.")
        return {"role": "admin"}

    return router

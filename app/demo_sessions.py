"""Demo publica con una copia por visitante.

Sin esto, todas las personas que abren el enlace compartirian los mismos datos: una que aislara un
correo, o pulsara «Reiniciar», cambiaria lo que ve la siguiente (incluido el jurado). Aqui cada
visitante recibe su propia aplicacion de demostracion (su propio estado, en memoria), identificada
por una cookie aleatoria. No hay cuentas ni datos reales: solo el estado simulado de cada visita.

Tambien pone limites de uso por direccion (visitas nuevas y escrituras por minuto) y un tope de
copias vivas, para que nadie pueda llenar la memoria del servicio gratuito.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import threading
import time
from collections import deque
from collections.abc import Callable

COOKIE = "atalaya_demo_sid"
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
# Rutas que no necesitan estado propio: no crean copia (la comprobacion de salud de la plataforma
# llega sin cookie cada pocos segundos y no debe llenar la memoria).
_SHARED_PREFIXES = ("/health", "/static/")
_STATEFUL_PREFIXES = ("/api/", "/auth/", "/invite/", "/connected", "/login")
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


class DemoSessions:
    """Aplicacion ASGI que reparte cada visitante a su propia copia de la demo."""

    def __init__(
        self,
        factory: Callable,
        *,
        max_sessions: int | None = None,
        ttl_seconds: int | None = None,
        writes_per_minute: int | None = None,
        new_sessions_per_minute: int | None = None,
        secure: bool | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._factory = factory
        self.max_sessions = max_sessions or _env_int("ATALAYA_DEMO_MAX_SESSIONS", 200)
        self.ttl = ttl_seconds or _env_int("ATALAYA_DEMO_TTL", 7200)
        self.writes_per_minute = writes_per_minute or _env_int(
            "ATALAYA_DEMO_WRITES_PER_MIN", 120
        )
        self.new_per_minute = new_sessions_per_minute or _env_int(
            "ATALAYA_DEMO_NEW_SESSIONS_PER_MIN", 20
        )
        if secure is None:
            secure = os.environ.get("ATALAYA_BASE_URL", "").startswith("https")
        self.secure = secure
        self._clock = clock
        self._lock = threading.Lock()
        self._sessions: dict[str, tuple[object, float]] = {}  # sid -> (app, ultimo uso)
        self._writes: dict[str, deque[float]] = {}
        self._new: dict[str, deque[float]] = {}
        self._shared = (
            factory()
        )  # sin estado de visitante: salud, archivos estaticos y 404

    # --- cuenta de copias vivas (para pruebas y diagnostico) --------------------------------
    def __len__(self) -> int:
        return len(self._sessions)

    # --- limites ------------------------------------------------------------------------------
    def _allowed(self, bucket: dict[str, deque[float]], key: str, limit: int) -> bool:
        now = self._clock()
        events = bucket.setdefault(key, deque())
        while events and now - events[0] > 60:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        if len(bucket) > 5000:  # no acumular direcciones para siempre
            for k in [k for k, v in bucket.items() if not v or now - v[-1] > 60]:
                del bucket[k]
        return True

    # --- copias -------------------------------------------------------------------------------
    def _evict(self, now: float) -> None:
        for sid in [
            s for s, (_, used) in self._sessions.items() if now - used > self.ttl
        ]:
            del self._sessions[sid]
        while len(self._sessions) >= self.max_sessions:
            oldest = min(self._sessions, key=lambda s: self._sessions[s][1])
            del self._sessions[oldest]

    def _get(self, sid: str | None) -> object | None:
        """La copia de este visitante, o None. Un sid desconocido NUNCA se adopta."""
        now = self._clock()
        with self._lock:
            if sid and _SID_RE.match(sid) and sid in self._sessions:
                app, used = self._sessions[sid]
                if now - used <= self.ttl:
                    self._sessions[sid] = (app, now)
                    return app
                del self._sessions[sid]
            return None

    def _create(self) -> tuple[object, str]:
        sid = secrets.token_urlsafe(24)
        app = self._factory()
        with self._lock:
            self._evict(self._clock())
            self._sessions[sid] = (app, self._clock())
        return app, sid

    # --- ASGI ---------------------------------------------------------------------------------
    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if scope["type"] != "http":  # la demo no usa websockets
            return
        path: str = scope["path"]
        client = (scope.get("client") or ("desconocido", 0))[0]
        method = scope["method"]

        if path.startswith(_SHARED_PREFIXES) or not (
            path == "/" or path.startswith(_STATEFUL_PREFIXES)
        ):
            await self._shared(scope, receive, send)
            return

        if method in _WRITE_METHODS and not self._allowed(
            self._writes, client, self.writes_per_minute
        ):
            await self._too_many(send)
            return

        cookies = _parse_cookies(scope)
        app = self._get(cookies.get(COOKIE))
        new_sid = None
        if app is None:
            if not self._allowed(self._new, client, self.new_per_minute):
                await self._too_many(send)
                return
            app, new_sid = self._create()

        if new_sid is None:
            await app(scope, receive, send)
            return

        cookie = (
            f"{COOKIE}={new_sid}; Path=/; HttpOnly; SameSite=Lax; Max-Age={self.ttl}"
        )
        if self.secure:
            cookie += "; Secure"

        async def send_with_cookie(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"set-cookie", cookie.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        await app(scope, receive, send_with_cookie)

    async def _too_many(self, send) -> None:
        body = json.dumps(
            {"detail": "Demasiadas solicitudes. Espera un momento e intenta de nuevo."}
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"retry-after", b"30"),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def _parse_cookies(scope) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, value in scope.get("headers", []):
        if name == b"cookie":
            for part in value.decode("latin-1").split(";"):
                key, _, val = part.strip().partition("=")
                if key and key not in out:
                    out[key] = val
    return out

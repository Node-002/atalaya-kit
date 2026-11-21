"""Demo publica con una copia por visitante.

Sin esto, todas las personas que abren el enlace compartirian los mismos datos: una que aislara un
correo, o pulsara «Reiniciar», cambiaria lo que ve la siguiente (incluido el jurado). Aqui cada
visitante recibe su propia aplicacion de demostracion (su propio estado, en memoria), identificada
por una cookie aleatoria. No hay cuentas ni datos reales: solo el estado simulado de cada visita.

Tambien pone limites de uso por direccion (visitas nuevas y escrituras por minuto) y un tope de
copias vivas, para que nadie pueda llenar la memoria del servicio gratuito.
"""

from __future__ import annotations

import asyncio
import ipaddress
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


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ.get(name, default)))
    except ValueError:
        return default


def client_ip(scope, trusted_hops: int) -> str:
    """Direccion del visitante, resistente a X-Forwarded-For falsificado.

    Cada proxy AGREGA al final de la cabecera la direccion de quien le hablo; lo que viene antes
    lo escribio el cliente y no es de fiar. Con `trusted_hops` proxies propios delante, la
    direccion real es la entrada numero `trusted_hops` contando desde la DERECHA (nunca la
    primera). Con 0 se ignora la cabecera (ejecucion local sin proxy). Si no es una IP valida se
    usa la del socket. Las IPv6 se agrupan por /64 (quien tiene un /64 controla 2^64 direcciones).
    """
    peer = (scope.get("client") or ("desconocido", 0))[0]
    ip = peer
    if trusted_hops > 0:
        parts: list[str] = []
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-for":
                parts += [p.strip() for p in value.decode("latin-1").split(",")]
        if len(parts) >= trusted_hops:
            ip = parts[-trusted_hops]
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return peer if peer != ip else "desconocido"
    if addr.version == 6:
        return str(ipaddress.ip_network(f"{addr}/64", strict=False).network_address)
    return str(addr)


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
        max_per_ip: int | None = None,
        global_new_per_minute: int | None = None,
        max_body: int | None = None,
        trusted_hops: int | None = None,
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
        self.max_per_ip = max_per_ip or _env_int("ATALAYA_DEMO_MAX_PER_IP", 10)
        self.global_new_per_minute = global_new_per_minute or _env_int(
            "ATALAYA_DEMO_GLOBAL_NEW_PER_MIN", 300
        )
        self.max_body = max_body or _env_int("ATALAYA_DEMO_MAX_BODY", 16384)
        self.trusted_hops = (
            trusted_hops
            if trusted_hops is not None
            else _env_int("ATALAYA_TRUSTED_HOPS", 0, minimum=0)
        )
        if secure is None:
            secure = os.environ.get("ATALAYA_BASE_URL", "").startswith("https")
        self.secure = secure
        self._clock = clock
        self._lock = threading.Lock()
        self._sessions: dict[str, tuple[object, float, str]] = {}  # sid -> (app, ultimo uso, ip)
        self._writes: dict[str, deque[float]] = {}
        self._sid_writes: dict[str, deque[float]] = {}
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
    def _evict(self, now: float, ip: str) -> None:
        """Hace sitio para una copia nueva de `ip` sin echar a otros visitantes por su culpa."""
        for sid in [
            s for s, (_, used, _ip) in self._sessions.items() if now - used > self.ttl
        ]:
            del self._sessions[sid]
        # Una sola direccion no puede acaparar copias: al pasar su tope pierde las suyas mas viejas.
        mine = [s for s, v in self._sessions.items() if v[2] == ip]
        mine.sort(key=lambda s: self._sessions[s][1])
        for sid in mine[: max(0, len(mine) - self.max_per_ip + 1)]:
            del self._sessions[sid]
        while len(self._sessions) >= self.max_sessions:
            # Lleno: se sacrifica la copia mas vieja de quien mas copias tiene (no la de un
            # visitante cualquiera), asi un inundador solo se desaloja a si mismo.
            counts: dict[str, int] = {}
            for _a, _u, owner in self._sessions.values():
                counts[owner] = counts.get(owner, 0) + 1
            top = max(counts, key=lambda o: counts[o])
            pool = [s for s, v in self._sessions.items() if v[2] == top]
            del self._sessions[min(pool, key=lambda s: self._sessions[s][1])]
        for sid in [s for s in self._sid_writes if s not in self._sessions]:
            del self._sid_writes[sid]

    def _get(self, sid: str | None) -> object | None:
        """La copia de este visitante, o None. Un sid desconocido NUNCA se adopta."""
        now = self._clock()
        with self._lock:
            if sid and _SID_RE.match(sid) and sid in self._sessions:
                app, used, owner = self._sessions[sid]
                if now - used <= self.ttl:
                    self._sessions[sid] = (app, now, owner)
                    return app
                del self._sessions[sid]
            return None

    def _create(self, ip: str) -> tuple[object, str]:
        sid = secrets.token_urlsafe(24)
        app = self._factory()
        with self._lock:
            self._evict(self._clock(), ip)
            self._sessions[sid] = (app, self._clock(), ip)
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
        method = scope["method"]
        client = client_ip(scope, self.trusted_hops)
        scope = {**scope, "client": (client, 0)}  # lo que ve el resto es la direccion ya validada

        if _body_too_big(scope, self.max_body):
            await self._reject(send, 413, "La solicitud es demasiado grande.")
            return

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
        sid = cookies.get(COOKIE)
        app = self._get(sid)
        new_sid = None
        if app is None:
            if not self._allowed(
                self._new, client, self.new_per_minute
            ) or not self._allowed(
                self._new, "*global*", self.global_new_per_minute
            ):
                await self._too_many(send)
                return
            # crear una copia cuesta CPU: fuera del bucle de eventos, para no frenar a los demas
            app, new_sid = await asyncio.to_thread(self._create, client)
        elif method in _WRITE_METHODS and not self._allowed(
            self._sid_writes, sid, self.writes_per_minute
        ):
            # tambien por cookie: cambiar de direccion no da mas escrituras a la misma copia
            await self._too_many(send)
            return

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
        await self._reject(
            send, 429, "Demasiadas solicitudes. Espera un momento e intenta de nuevo."
        )

    async def _reject(self, send, status: int, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    *([(b"retry-after", b"30")] if status == 429 else []),
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def _body_too_big(scope, limit: int) -> bool:
    """Cuerpo mayor al tope, o con Transfer-Encoding (la app nunca envia por trozos)."""
    for name, value in scope.get("headers", []):
        if name == b"transfer-encoding":
            return True
        if name == b"content-length":
            try:
                if int(value) > limit:
                    return True
            except ValueError:
                return True
    return False


def _parse_cookies(scope) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, value in scope.get("headers", []):
        if name == b"cookie":
            for part in value.decode("latin-1").split(";"):
                key, _, val = part.strip().partition("=")
                if key and key not in out:
                    out[key] = val
    return out

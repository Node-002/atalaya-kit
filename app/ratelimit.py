"""Limite de intentos de acceso: progresivo, persistente y por direccion.

Politica (ver docs/REVISION_SEGURIDAD.md):
- 5 fallos dentro de una ventana de 15 minutos bloquean a esa direccion.
- El bloqueo dura 15 min y se DUPLICA en cada reincidencia (hasta 24 h).
- Se guarda en la base: reiniciar el servidor no reinicia el contador.
- Un acceso correcto borra los fallos pero no el nivel; el nivel baja tras 24 h sin fallos.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.db import Database

MAX_FAILURES = 5
WINDOW = timedelta(minutes=15)
BASE_LOCK = timedelta(minutes=15)
MAX_LOCK = timedelta(hours=24)
LEVEL_RESET = timedelta(hours=24)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class LockEvent:
    client: str
    until: datetime
    level: int
    failures: int


class RateLimiter:
    def __init__(self, db: Database, now: Callable[[], datetime] = _utcnow) -> None:
        self._db = db
        self._now = now

    def _row(self, client: str):
        rows = self._db.query("SELECT * FROM login_limits WHERE client = ?", (client,))
        return rows[0] if rows else None

    def retry_after(self, client: str) -> int:
        """Segundos que faltan para poder intentar de nuevo (0 si puede)."""
        row = self._row(client)
        if row is None or not row["locked_until"]:
            return 0
        remaining = (
            datetime.fromisoformat(row["locked_until"]) - self._now()
        ).total_seconds()
        return max(0, int(remaining) + (1 if remaining % 1 else 0))

    def register_failure(self, client: str) -> LockEvent | None:
        """Cuenta un fallo. Devuelve un LockEvent solo cuando ESTE fallo provoca el bloqueo."""
        now = self._now()
        row = self._row(client)
        failures, level = 0, 0
        window_start = now
        if row is not None:
            level = row["level"]
            last = (
                datetime.fromisoformat(row["last_failure"])
                if row["last_failure"]
                else None
            )
            if last and now - last > LEVEL_RESET:
                level = 0
            if (
                row["window_start"]
                and now - datetime.fromisoformat(row["window_start"]) <= WINDOW
            ):
                failures = row["failures"]
                window_start = datetime.fromisoformat(row["window_start"])
        failures += 1
        locked_until, event = None, None
        if failures >= MAX_FAILURES:
            lock = min(BASE_LOCK * (2**level), MAX_LOCK)
            locked_until = now + lock
            event = LockEvent(client, locked_until, level, failures)
            level += 1
            failures = 0
            window_start = now
        self._db.execute(
            "INSERT INTO login_limits (client, failures, window_start, locked_until, level, last_failure) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(client) DO UPDATE SET "
            "failures = excluded.failures, window_start = excluded.window_start, "
            "locked_until = COALESCE(excluded.locked_until, login_limits.locked_until), "
            "level = excluded.level, last_failure = excluded.last_failure",
            (
                client,
                failures,
                window_start.isoformat(),
                locked_until.isoformat() if locked_until else None,
                level,
                now.isoformat(),
            ),
        )
        return event

    def register_success(self, client: str) -> None:
        self._db.execute(
            "UPDATE login_limits SET failures = 0, window_start = NULL WHERE client = ?",
            (client,),
        )

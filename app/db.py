"""SQLite minimo. Guarda buzones (con el token cifrado), invitaciones y auditoria.

NO guarda cuerpos de correo ni adjuntos. Las alertas siguen en memoria por ahora.
"""

import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS mailboxes (
    id          TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    email       TEXT UNIQUE,
    kind        TEXT NOT NULL DEFAULT 'gmail',
    token_enc   BLOB,
    created_at  TEXT NOT NULL,
    consent_at  TEXT,
    invite_id   TEXT
);
CREATE TABLE IF NOT EXISTS invites (
    id          TEXT PRIMARY KEY,
    token_hash  TEXT UNIQUE NOT NULL,
    label       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    used_at     TEXT,
    revoked_at  TEXT,
    mailbox_id  TEXT
);
CREATE TABLE IF NOT EXISTS login_limits (
    client        TEXT PRIMARY KEY,
    failures      INTEGER NOT NULL DEFAULT 0,
    window_start  TEXT,
    locked_until  TEXT,
    level         INTEGER NOT NULL DEFAULT 0,
    last_failure  TEXT
);
CREATE TABLE IF NOT EXISTS security_events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    at      TEXT NOT NULL,
    kind    TEXT NOT NULL,
    detail  TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS alerts (
    id          TEXT PRIMARY KEY,
    mailbox_id  TEXT NOT NULL,
    ref         TEXT NOT NULL,
    data        BLOB NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    at      TEXT NOT NULL,
    actor   TEXT NOT NULL,
    action  TEXT NOT NULL,
    detail  TEXT NOT NULL DEFAULT ''
);
"""


class Database:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> int:
        """Ejecuta una escritura y devuelve las filas afectadas."""
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur.rowcount

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

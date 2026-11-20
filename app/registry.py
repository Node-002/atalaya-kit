"""Registro de buzones, invitaciones y auditoria (ver docs/adr/0003).

- El token de invitacion solo se devuelve UNA vez; en la base queda su hash SHA-256.
- Los tokens OAuth de cada buzon se guardan cifrados (Fernet).
- Una invitacion es de un solo uso y vence (48 h por defecto).
"""

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta

from cryptography.fernet import Fernet, InvalidToken

from app.db import Database

INVITE_TTL = timedelta(hours=48)
LABEL_MAX = 80


def _now() -> datetime:
    return datetime.now(UTC)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class MailboxVault:
    """Interfaz load/save/delete que usa GmailProvider, respaldada por la base."""

    def __init__(self, registry: "Registry", mailbox_id: str) -> None:
        self._registry = registry
        self._mailbox_id = mailbox_id

    def load(self) -> dict | None:
        return self._registry.load_token(self._mailbox_id)

    def save(self, data: dict) -> None:
        self._registry.save_token(self._mailbox_id, data)

    def delete(self) -> None:
        self._registry.clear_token(self._mailbox_id)


class Registry:
    def __init__(self, db: Database, fernet: Fernet) -> None:
        self.db = db
        self._fernet = fernet

    # --- Auditoria ----------------------------------------------------------------
    def audit(self, actor: str, action: str, detail: str = "") -> None:
        self.db.execute(
            "INSERT INTO audit (at, actor, action, detail) VALUES (?, ?, ?, ?)",
            (_now().isoformat(), actor, action, detail[:200]),
        )

    def list_audit(self, limit: int = 50) -> list[dict]:
        rows = self.db.query(
            "SELECT at, actor, action, detail FROM audit ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]

    def count_audit(self, actions: tuple[str, ...], since: datetime) -> int:
        total = 0
        for action in actions:
            rows = self.db.query(
                "SELECT COUNT(*) AS n FROM audit WHERE action = ? AND at >= ?",
                (action, since.isoformat()),
            )
            total += int(rows[0]["n"])
        return total

    # --- Eventos de seguridad (los que se avisan a otras personas) -----------------------
    def log_security_event(self, kind: str, detail: str = "") -> None:
        self.db.execute(
            "INSERT INTO security_events (at, kind, detail) VALUES (?, ?, ?)",
            (_now().isoformat(), kind, detail[:300]),
        )

    def list_security_events(self, hours: int = 24, limit: int = 20) -> list[dict]:
        since = (_now() - timedelta(hours=hours)).isoformat()
        rows = self.db.query(
            "SELECT at, kind, detail FROM security_events WHERE at >= ? ORDER BY id DESC LIMIT ?",
            (since, limit),
        )
        return [dict(r) for r in rows]

    # --- Invitaciones --------------------------------------------------------------
    def create_invite(
        self, label: str, actor: str, ttl: timedelta = INVITE_TTL
    ) -> tuple[str, str]:
        """Devuelve (id, token). El token no se puede recuperar despues."""
        label = label.strip()[:LABEL_MAX]
        if not label:
            raise ValueError("La invitacion necesita un nombre o puesto.")
        token = secrets.token_urlsafe(32)
        invite_id = secrets.token_hex(8)
        now = _now()
        self.db.execute(
            "INSERT INTO invites (id, token_hash, label, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (invite_id, _hash(token), label, now.isoformat(), (now + ttl).isoformat()),
        )
        self.audit(actor, "invite_created", label)
        return invite_id, token

    @staticmethod
    def _invite_status(row: dict) -> str:
        if row["revoked_at"]:
            return "revoked"
        if row["used_at"]:
            return "used"
        if row["expires_at"] <= _now().isoformat():
            return "expired"
        return "pending"

    def _invite_dict(self, row) -> dict:
        data = dict(row)
        data["status"] = self._invite_status(data)
        data.pop("token_hash", None)
        return data

    def find_invite(self, token: str) -> dict | None:
        rows = self.db.query(
            "SELECT * FROM invites WHERE token_hash = ?", (_hash(token),)
        )
        return self._invite_dict(rows[0]) if rows else None

    def list_invites(self) -> list[dict]:
        rows = self.db.query("SELECT * FROM invites ORDER BY created_at DESC LIMIT 100")
        return [self._invite_dict(r) for r in rows]

    def revoke_invite(self, invite_id: str, actor: str) -> bool:
        changed = self.db.execute(
            "UPDATE invites SET revoked_at = ? WHERE id = ? AND used_at IS NULL AND revoked_at IS NULL",
            (_now().isoformat(), invite_id),
        )
        if changed:
            self.audit(actor, "invite_revoked", invite_id)
        return bool(changed)

    def consume_invite(self, invite_id: str, mailbox_id: str) -> bool:
        """Marca la invitacion como usada de forma atomica. False si ya no es valida."""
        now = _now().isoformat()
        return bool(
            self.db.execute(
                "UPDATE invites SET used_at = ?, mailbox_id = ? "
                "WHERE id = ? AND used_at IS NULL AND revoked_at IS NULL AND expires_at > ?",
                (now, mailbox_id, invite_id, now),
            )
        )

    # --- Buzones ----------------------------------------------------------------------
    def add_mailbox(
        self,
        label: str,
        email: str,
        kind: str = "gmail",
        invite_id: str | None = None,
        consent: bool = False,
        token: dict | None = None,
        mailbox_id: str | None = None,
    ) -> str:
        """Crea el buzon, o actualiza el token si ese correo ya estaba (reconexion)."""
        existing = self.db.query("SELECT id FROM mailboxes WHERE email = ?", (email,))
        if existing:
            mailbox_id = existing[0]["id"]
            if token is not None:
                self.save_token(mailbox_id, token)
            self.audit("sistema", "mailbox_reconnected", email)
            return mailbox_id
        mailbox_id = mailbox_id or "mb_" + secrets.token_hex(6)
        now = _now().isoformat()
        self.db.execute(
            "INSERT INTO mailboxes (id, label, email, kind, token_enc, created_at, consent_at, invite_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                mailbox_id,
                label.strip()[:LABEL_MAX],
                email,
                kind,
                self._encrypt(token) if token is not None else None,
                now,
                now if consent else None,
                invite_id,
            ),
        )
        self.audit("sistema", "mailbox_connected", email)
        return mailbox_id

    def list_mailboxes(self, kind: str | None = None) -> list[dict]:
        sql = "SELECT id, label, email, kind, created_at, consent_at FROM mailboxes"
        rows = self.db.query(
            sql + (" WHERE kind = ?" if kind else "") + " ORDER BY created_at",
            (kind,) if kind else (),
        )
        return [dict(r) for r in rows]

    def find_mailbox_by_email(self, email: str) -> dict | None:
        rows = self.db.query(
            "SELECT id, label, email, kind, created_at, consent_at FROM mailboxes WHERE email = ?",
            (email,),
        )
        return dict(rows[0]) if rows else None

    def get_mailbox(self, mailbox_id: str) -> dict | None:
        rows = self.db.query(
            "SELECT id, label, email, kind, created_at, consent_at FROM mailboxes WHERE id = ?",
            (mailbox_id,),
        )
        return dict(rows[0]) if rows else None

    def delete_mailbox(self, mailbox_id: str, actor: str) -> bool:
        box = self.get_mailbox(mailbox_id)
        changed = self.db.execute("DELETE FROM mailboxes WHERE id = ?", (mailbox_id,))
        if changed:
            self.audit(
                actor, "mailbox_disconnected", (box or {}).get("email") or mailbox_id
            )
        return bool(changed)

    def vault(self, mailbox_id: str) -> MailboxVault:
        return MailboxVault(self, mailbox_id)

    # --- Tokens OAuth cifrados ---------------------------------------------------------
    def _encrypt(self, data: dict) -> bytes:
        return self._fernet.encrypt(json.dumps(data).encode())

    def load_token(self, mailbox_id: str) -> dict | None:
        rows = self.db.query(
            "SELECT token_enc FROM mailboxes WHERE id = ?", (mailbox_id,)
        )
        if not rows or rows[0]["token_enc"] is None:
            return None
        try:
            return json.loads(self._fernet.decrypt(rows[0]["token_enc"]))
        except (InvalidToken, ValueError):
            return None

    def save_token(self, mailbox_id: str, data: dict) -> None:
        self.db.execute(
            "UPDATE mailboxes SET token_enc = ? WHERE id = ?",
            (self._encrypt(data), mailbox_id),
        )

    def clear_token(self, mailbox_id: str) -> None:
        self.db.execute(
            "UPDATE mailboxes SET token_enc = NULL WHERE id = ?", (mailbox_id,)
        )

    # --- Alertas (cifradas en reposo; sin cuerpos ni adjuntos) ---------------------------
    def save_alert(self, alert_id: str, mailbox_id: str, ref: str, data: dict) -> None:
        self.db.execute(
            "INSERT INTO alerts (id, mailbox_id, ref, data, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
            (alert_id, mailbox_id, ref, self._encrypt(data), _now().isoformat()),
        )

    def load_alerts(self) -> list[tuple[str, str, str, dict]]:
        out = []
        for row in self.db.query("SELECT id, mailbox_id, ref, data FROM alerts"):
            try:
                data = json.loads(self._fernet.decrypt(row["data"]))
            except (InvalidToken, ValueError):
                continue  # clave distinta o dato danado: se ignora, no se rompe el arranque
            out.append((row["id"], row["mailbox_id"], row["ref"], data))
        return out

    def delete_alerts(self, mailbox_id: str | None = None) -> None:
        if mailbox_id is None:
            self.db.execute("DELETE FROM alerts")
        else:
            self.db.execute("DELETE FROM alerts WHERE mailbox_id = ?", (mailbox_id,))

"""Proveedor de Gmail. Solo uso local con usuarios de prueba (modo 'gmail').

Permiso solicitado: gmail.modify (minimo que permite etiquetar). El codigo NUNCA
borra ni envia correos: esas operaciones no existen en esta clase.
"""

import base64
import json
import logging
import re
from datetime import UTC, datetime

from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models import ConnectionStatus, Label, Message
from app.tokens import TokenVault

log = logging.getLogger("atalaya.gmail")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
BODY_LIMIT = 4000
_LINK_RE = re.compile(r"https?://[^\s<>\"')]+")
_TAG_RE = re.compile(r"<[^>]+>")


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
        "utf-8", "replace"
    )


def _extract_body(payload: dict) -> str:
    """Prefiere text/plain; si solo hay HTML, quita las etiquetas. Recorta el resultado."""
    plain: list[str] = []
    html: list[str] = []

    def walk(part: dict) -> None:
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            html.append(_TAG_RE.sub(" ", _decode(data)))
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    text = "\n".join(plain) or "\n".join(html)
    return text[:BODY_LIMIT]


def parse_message(raw: dict) -> Message:
    headers = {
        h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])
    }
    body = _extract_body(raw.get("payload", {}))
    received = datetime.fromtimestamp(int(raw.get("internalDate", "0")) / 1000, tz=UTC)
    return Message(
        ref=raw["id"],
        received_at=received,
        sender=headers.get("from", ""),
        reply_to=headers.get("reply-to"),
        subject=headers.get("subject", ""),
        body=body,
        headers={"Authentication-Results": headers.get("authentication-results", "")},
        links=_LINK_RE.findall(body)[:20],
    )


class GmailProvider:
    def __init__(
        self, vault: TokenVault, client_secrets: dict, max_messages: int = 5
    ) -> None:
        self.vault = vault
        self._client = client_secrets["web"]
        self.max_messages = max_messages
        self._seen: set[str] = set()
        self._label_ids: dict[str, str] = {}
        self._account: str | None = None

    # -- credenciales y servicio -------------------------------------------------
    def _credentials(self) -> Credentials | None:
        data = self.vault.load()
        if not data:
            return None
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=self._client["token_uri"],
            client_id=self._client["client_id"],
            client_secret=self._client["client_secret"],
            scopes=SCOPES,
        )
        if not creds.valid:
            creds.refresh(Request())
            self.vault.save(
                {"token": creds.token, "refresh_token": creds.refresh_token}
            )
        return creds

    def _service(self):
        creds = self._credentials()
        if creds is None:
            return None
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def reset_cache(self) -> None:
        self._seen.clear()
        self._label_ids.clear()
        self._account = None

    # -- MailProvider ----------------------------------------------------------
    def list_new_messages(self) -> list[Message]:
        try:
            service = self._service()
            if service is None:
                return []
            listing = (
                service.users()
                .messages()
                .list(userId="me", labelIds=["INBOX"], maxResults=self.max_messages)
                .execute()
            )
            found: list[Message] = []
            for item in listing.get("messages", []):
                if item["id"] in self._seen:
                    continue
                raw = (
                    service.users()
                    .messages()
                    .get(userId="me", id=item["id"], format="full")
                    .execute()
                )
                self._seen.add(item["id"])
                found.append(parse_message(raw))
            return found
        except (GoogleAuthError, HttpError) as exc:
            log.warning("No se pudo leer Gmail: %s", type(exc).__name__)
            return []

    def _label_id(self, service, name: str) -> str:
        if name not in self._label_ids:
            labels = (
                service.users().labels().list(userId="me").execute().get("labels", [])
            )
            self._label_ids = {lb["name"]: lb["id"] for lb in labels} | self._label_ids
        if name not in self._label_ids:
            created = (
                service.users()
                .labels()
                .create(
                    userId="me",
                    body={
                        "name": name,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    },
                )
                .execute()
            )
            self._label_ids[name] = created["id"]
        return self._label_ids[name]

    def _modify(self, ref: str, add: list[str], remove: list[str]) -> None:
        service = self._service()
        if service is None:
            raise RuntimeError("Gmail no esta conectado.")
        service.users().messages().modify(
            userId="me", id=ref, body={"addLabelIds": add, "removeLabelIds": remove}
        ).execute()

    def apply_label(self, ref: str, label: Label) -> None:
        service = self._service()
        if service is None:
            raise RuntimeError("Gmail no esta conectado.")
        self._modify(ref, [self._label_id(service, label.value)], [])

    def quarantine(self, ref: str) -> None:
        """Quitar de la bandeja + etiqueta. Reversible; no borra nada."""
        service = self._service()
        if service is None:
            raise RuntimeError("Gmail no esta conectado.")
        self._modify(ref, [self._label_id(service, Label.suspicious.value)], ["INBOX"])

    def release(self, ref: str) -> None:
        service = self._service()
        if service is None:
            raise RuntimeError("Gmail no esta conectado.")
        remove = [
            self._label_id(service, Label.suspicious.value),
            self._label_id(service, Label.review.value),
        ]
        self._modify(ref, ["INBOX"], remove)

    def connection_status(self) -> ConnectionStatus:
        try:
            service = self._service()
            if service is None:
                return ConnectionStatus.revoked
            profile = service.users().getProfile(userId="me").execute()
            self._account = profile.get("emailAddress")
            return ConnectionStatus.connected
        except RefreshError:
            return ConnectionStatus.revoked
        except HttpError as exc:
            return (
                ConnectionStatus.revoked
                if exc.resp.status in (401, 403)
                else ConnectionStatus.error
            )
        except GoogleAuthError:
            return ConnectionStatus.error

    def account_name(self) -> str:
        return self._account or "Gmail (sin conectar)"


def load_client_secrets(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

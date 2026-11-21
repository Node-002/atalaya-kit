"""Modelos del contrato de Atalaya (ver docs/adr/0001 y PRD.md, seccion 8)."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, computed_field


class Risk(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Status(str, Enum):
    new = "new"
    labeled = "labeled"
    pending_approval = "pending_approval"
    quarantined = "quarantined"
    dismissed = "dismissed"


class Label(str, Enum):
    review = "Revisar"
    suspicious = "Sospechoso"


class ConnectionStatus(str, Enum):
    connected = "connected"
    revoked = "revoked"
    error = "error"


class Message(BaseModel):
    """Correo en memoria. NUNCA se persiste el cuerpo (regla de privacidad)."""

    ref: str
    received_at: datetime
    sender: str
    reply_to: str | None = None
    subject: str
    body: str
    headers: dict[str, str] = Field(default_factory=dict)
    links: list[str] = Field(default_factory=list)


class Signal(BaseModel):
    code: str
    description: str
    weight: int


HUMAN_ACTIONS = (
    "quarantine",
    "reject_quarantine",
    "mark_legit",
)  # decisiones de una persona


class ActionRecord(BaseModel):
    type: str
    at: datetime
    by: str
    reason: str | None = None  # motivo escrito por la persona


class Alert(BaseModel):
    id: str
    message_ref: str  # hash, no el contenido
    mailbox_id: str = "default"
    mailbox_label: str = ""
    received_at: datetime
    sender_domain: str
    risk: Risk
    signals: list[Signal]
    explanation: str
    explanation_source: Literal["rules", "ai", "simulated"] = "rules"
    status: Status
    actions: list[ActionRecord] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def priority(self) -> int:
        """0 = decidir ya, 1 = revisar, 2 = en cuarentena, 3 = ya revisado por una persona,
        4 = nunca fue sospechoso."""
        if self.status is Status.pending_approval:
            return 0
        if (
            self.risk is Risk.medium
            and self.status is Status.labeled
            and not self.reviewed
        ):
            return 1
        if self.status is Status.quarantined:
            return 2
        if self.reviewed:
            return 3
        return 4

    @computed_field  # type: ignore[prop-decorator]
    @property
    def reviewed(self) -> bool:
        """Una persona ya tomo una decision sobre este correo."""
        return any(a.type in HUMAN_ACTIONS for a in self.actions)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def quarantine_needs_reason(self) -> bool:
        """Aislar lo que Atalaya YA marco como alto es un clic; lo demas exige motivo."""
        return self.status is not Status.pending_approval


class Coverage(BaseModel):
    mailbox_id: str = "default"
    label: str = ""
    account: str
    status: ConnectionStatus
    last_check: datetime | None = None  # ultima vez que Atalaya reviso este buzon

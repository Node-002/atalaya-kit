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


class ActionRecord(BaseModel):
    type: str
    at: datetime
    by: str


class Alert(BaseModel):
    id: str
    message_ref: str  # hash, no el contenido
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
        """0 = decidir ya, 1 = revisar, 2 = atendido con riesgo, 3 = sin accion pendiente."""
        if self.status is Status.pending_approval:
            return 0
        if self.risk is Risk.medium and self.status is Status.labeled:
            return 1
        if self.status is Status.quarantined or (
            self.risk is Risk.high and self.status is Status.labeled
        ):
            return 2
        return 3


class Coverage(BaseModel):
    account: str
    status: ConnectionStatus

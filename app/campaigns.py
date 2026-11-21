"""Campanas: el mismo ataque llegando a varios buzones de la organizacion.

El codigo calcula el agrupamiento; no se guarda ningun cuerpo. Solo se conservan dos huellas
(hash) por alerta: la del remitente y la del dominio + asunto normalizado. Dos alertas de buzones
distintos pertenecen a la misma campana si comparten alguna de las dos huellas.
"""

import hashlib
import re
from email.utils import parseaddr

from pydantic import BaseModel

from app.models import Alert, Risk, Status

_PREFIX = re.compile(r"^\s*((re|rv|fw|fwd)\s*:\s*)+", re.IGNORECASE)
_NOISE = re.compile(r"[^a-zà-ÿ ]+")


def _hash(kind: str, value: str) -> str:
    return hashlib.sha256(f"{kind}:{value}".encode()).hexdigest()[:16]


def normalize_subject(subject: str) -> str:
    """Sin Re:/Fwd:, en minusculas, sin numeros ni signos: 'URGENTE 2' y 'urgente' coinciden."""
    text = _PREFIX.sub("", subject).lower()
    return " ".join(_NOISE.sub(" ", text).split())


def fingerprints(sender: str, subject: str, domain: str) -> tuple[str, str]:
    """(huella del remitente, huella de dominio + asunto). Vacias si no hay datos."""
    address = parseaddr(sender)[1].strip().lower()
    topic = normalize_subject(subject)
    return (
        _hash("s", address) if address else "",
        _hash("t", f"{domain}|{topic}") if topic and domain else "",
    )


class Campaign(BaseModel):
    id: str
    sender_domain: str
    risk: Risk
    mailbox_count: int
    mailboxes: list[str]
    alert_ids: list[str]
    actionable: int  # alertas que aun no estan en cuarentena
    pending: int  # alertas que esperan decision (riesgo alto sin decidir)
    needs_reason: bool  # alguna exige motivo escrito para aislarla


def _components(alerts: list[Alert]) -> list[list[Alert]]:
    parent = list(range(len(alerts)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen: dict[str, int] = {}
    for i, alert in enumerate(alerts):
        for key in (alert.sender_key, alert.topic_key):
            if not key:
                continue
            if key in seen:
                parent[find(i)] = find(seen[key])
            else:
                seen[key] = i
    groups: dict[int, list[Alert]] = {}
    for i, alert in enumerate(alerts):
        groups.setdefault(find(i), []).append(alert)
    return list(groups.values())


def find_campaigns(alerts: list[Alert]) -> list[Campaign]:
    """Grupos de alertas sospechosas (riesgo medio o alto) de 2 o mas buzones."""
    suspicious = [a for a in alerts if a.risk is not Risk.low]
    found = []
    for group in _components(suspicious):
        boxes = {a.mailbox_id for a in group}
        if len(boxes) < 2:
            continue
        ids = sorted(a.id for a in group)
        open_ = [a for a in group if a.status is not Status.quarantined]
        domains = sorted({a.sender_domain for a in group})
        found.append(
            Campaign(
                id=hashlib.sha256("|".join(ids).encode()).hexdigest()[:12],
                sender_domain=domains[0],
                risk=Risk.high if any(a.risk is Risk.high for a in group) else Risk.medium,
                mailbox_count=len(boxes),
                mailboxes=sorted({a.mailbox_label or a.mailbox_id for a in group}),
                alert_ids=ids,
                actionable=len(open_),
                pending=sum(a.status is Status.pending_approval for a in group),
                needs_reason=any(a.quarantine_needs_reason for a in open_),
            )
        )
    return sorted(found, key=lambda c: (-c.pending, -c.mailbox_count, c.id))

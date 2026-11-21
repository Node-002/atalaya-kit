"""Informe de revision de un correo: que detecto Atalaya, que decidio cada persona y por que.

No incluye el contenido del correo ni sus adjuntos (Atalaya no los guarda).
"""

from datetime import UTC, datetime

from app.models import HUMAN_ACTIONS, Alert, Status

RISK_TEXT = {"high": "alto", "medium": "medio", "low": "bajo"}
DECISION_TEXT = {
    "quarantine": "Puso el correo en cuarentena (fuera de la bandeja)",
    "reject_quarantine": "Decidio no aislarlo y dejarlo donde estaba",
    "mark_legit": "Lo marco como legitimo y lo devolvio a la bandeja",
}
STATUS_TEXT = {
    Status.new: "Nuevo",
    Status.labeled: "Etiquetado, sin aislar",
    Status.pending_approval: "Pendiente de decision humana",
    Status.quarantined: "En cuarentena",
    Status.dismissed: "Sin accion pendiente",
}
SOURCE_TEXT = {
    "rules": "reglas automaticas",
    "ai": "IA",
    "simulated": "resumen simulado (sin IA real)",
}


def _final_state(alert: Alert) -> str:
    """Estado en palabras: distingue lo revisado por una persona de lo que nunca fue sospechoso."""
    human = [a for a in alert.actions if a.type in HUMAN_ACTIONS]
    if alert.status is Status.quarantined:
        return "En cuarentena (fuera de la bandeja)"
    if human and human[-1].type == "mark_legit":
        return "Revisado por una persona: devuelto a la bandeja como legitimo"
    if human and human[-1].type == "reject_quarantine":
        return "Revisado por una persona: se dejo sin aislar"
    return STATUS_TEXT[alert.status]


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _when(at: datetime) -> str:
    return at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def build_report(alert: Alert) -> str:
    score = sum(s.weight for s in alert.signals)
    human = [a for a in alert.actions if a.type in HUMAN_ACTIONS]
    lines = [
        "# Informe de revision de un correo",
        "",
        f"- Identificador de la alerta: {alert.id}",
        f"- Buzon: {alert.mailbox_label or '(sin nombre)'}",
        f"- Dominio del remitente: {alert.sender_domain}",
        f"- Recibido: {_when(alert.received_at)}",
        f"- Estado actual: {_final_state(alert)}",
        "",
        "## 1. Que detecto Atalaya (automatico)",
        "",
        f"- Riesgo: {RISK_TEXT[alert.risk.value]} ({score} puntos)",
        f"- Resumen: {_one_line(alert.explanation)} (origen: {SOURCE_TEXT[alert.explanation_source]})",
        "- Senales:",
    ]
    lines += [f"  - {s.description} ({s.weight} puntos)" for s in alert.signals] or [
        "  - Ninguna"
    ]
    lines += ["", "## 2. Decisiones de las personas", ""]
    if not human:
        lines.append("Todavia no hay decisiones humanas sobre este correo.")
    for n, action in enumerate(human, start=1):
        lines += [
            f"{n}. {_when(action.at)} - {action.by}",
            f"   - Decision: {DECISION_TEXT.get(action.type, action.type)}",
            f"   - Motivo: {_one_line(action.reason) if action.reason else '(sin motivo escrito: acepto el analisis de Atalaya)'}",
        ]
    lines += [
        "",
        "## 3. Resultado",
        "",
        f"Estado final: {_final_state(alert)}.",
        "",
        "---",
        f"Informe generado el {_when(datetime.now(UTC))}. No incluye el contenido del correo ni sus adjuntos.",
        "",
    ]
    return "\n".join(lines)

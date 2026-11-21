"""Informe de revision de un correo: que detecto Atalaya, que decidio cada persona y por que.

No incluye el contenido del correo ni sus adjuntos (Atalaya no los guarda).
"""

from collections import Counter
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
    lines += ["", "## Datos tecnicos del mensaje (solo cabeceras)", ""]
    f = alert.ficha
    if f is None:
        lines.append("Sin datos tecnicos guardados para este correo.")
    else:
        lines += [
            f"- Autenticacion: SPF {f.spf or 'sin dato'}, DKIM {f.dkim or 'sin dato'}, DMARC {f.dmarc or 'sin dato'}",
            f"- IP de origen: {f.source_ip or 'no encontrada'} (el pais no se consulta)",
            f"- Vector de ataque: {f.vector or '-'}",
            f"- Return-Path: {f.return_path or '-'}",
            f"- Dominio de Reply-To: {f.reply_to_domain or '-'}",
            f"- Enlaces (host neutralizado): {', '.join(f.link_hosts) or '-'}",
        ]
        lines += [f"  - {_one_line(h)}" for h in f.smtp]
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


AUDIT_TEXT = {
    "admin_login": "Inicio de sesion",
    "admin_login_failed": "Intento de acceso fallido",
    "admin_login_denied": "Cuenta no autorizada intento entrar",
    "admin_login_blocked": "Acceso bloqueado por demasiados intentos",
    "invite_created": "Creo una invitacion",
    "invite_revoked": "Revoco una invitacion",
    "mailbox_connected": "Se conecto un buzon",
    "mailbox_reconnected": "Se reconecto un buzon",
    "mailbox_disconnected": "Se desconecto un buzon",
    "mailbox_department_changed": "Cambio el area de un buzon",
    "mailbox_rejected_identity": "Se rechazo una cuenta con caracteres sospechosos",
    "alert_quarantine": "Puso un correo en cuarentena",
    "alert_kept": "Decidio no aislar un correo",
    "alert_legit": "Saco un correo de cuarentena o lo marco como legitimo",
}


def build_org_report(org_name: str, alerts: list[Alert], audit: list[dict]) -> str:
    """Reporte de la organizacion para la supervision: que se hizo, quien decidio y cuando.
    Solo veredictos, decisiones y motivos; nunca el contenido de los correos."""
    decisions = sorted(
        (
            (action.at, action.by, alert, action)
            for alert in alerts
            for action in alert.actions
            if action.type in HUMAN_ACTIONS
        ),
        key=lambda row: row[0],
        reverse=True,
    )
    risks = Counter(alert.risk.value for alert in alerts)
    states = Counter(_final_state(alert) for alert in alerts)
    lines = [
        f"# Reporte de la organizacion: {org_name}",
        "",
        f"Generado el {_when(datetime.now(UTC))}. No incluye el contenido de los correos.",
        "",
        "## 1. Resumen",
        "",
        f"- Correos analizados: {len(alerts)}",
        f"- Por riesgo: alto {risks['high']}, medio {risks['medium']}, bajo {risks['low']}",
    ]
    lines += [f"- {state}: {n}" for state, n in sorted(states.items())]
    lines += ["", "## 2. Decisiones de las personas (mas recientes primero)", ""]
    if not decisions:
        lines.append("Todavia no hay decisiones humanas.")
    for at, by, alert, action in decisions:
        reason = _one_line(action.reason) if action.reason else "(sin motivo escrito)"
        lines.append(
            f"- {_when(at)} - {by} - {alert.department} - {alert.mailbox_label or 'buzon'} / "
            f"{alert.sender_domain}: {DECISION_TEXT.get(action.type, action.type)}. Motivo: {reason}"
        )
    lines += ["", "## 3. Actividad registrada", ""]
    if not audit:
        lines.append("Sin actividad registrada.")
    for event in audit:
        text = AUDIT_TEXT.get(event["action"], event["action"])
        detail = f" ({_one_line(event['detail'])})" if event.get("detail") else ""
        lines.append(f"- {event['at']} - {event['actor']} - {text}{detail}")
    lines.append("")
    return "\n".join(lines)

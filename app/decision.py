"""Motor de decision: nivel de riesgo y accion permitida."""

from app.models import Label, Risk, Signal, Status

MEDIUM_AT = 30
HIGH_AT = 60


def score(signals: list[Signal]) -> int:
    return sum(s.weight for s in signals)


def risk_of(signals: list[Signal]) -> Risk:
    total = score(signals)
    if total >= HIGH_AT:
        return Risk.high
    if total >= MEDIUM_AT:
        return Risk.medium
    return Risk.low


def plan_for(risk: Risk) -> tuple[Label | None, Status]:
    """Bajo: nada. Medio: etiqueta Revisar. Alto: etiqueta Sospechoso y pide aprobacion."""
    if risk is Risk.high:
        return Label.suspicious, Status.pending_approval
    if risk is Risk.medium:
        return Label.review, Status.labeled
    return None, Status.dismissed


def explain(signals: list[Signal]) -> str:
    """Explicacion por plantilla. La explicacion con IA (JSON validado) llega el sabado."""
    if not signals:
        return "No se encontraron senales de riesgo."
    return " ".join(s.description for s in signals)

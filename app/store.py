"""Almacen de alertas en memoria (version del viernes). SQLite llega despues.

Guarda veredicto, senales, hash de referencia y estado. Nunca cuerpos ni adjuntos.
"""

import hashlib
import threading
from datetime import UTC, datetime

from app import analyzers, decision
from app.llm import Explainer, LLMVerdict, semantic_signals
from app.models import ActionRecord, Alert, Message, Risk, Signal, Status
from app.providers.base import MailProvider


def _ref_hash(ref: str) -> str:
    return hashlib.sha256(ref.encode()).hexdigest()[:16]


def _now() -> datetime:
    return datetime.now(UTC)


class AlertStore:
    def __init__(
        self,
        provider: MailProvider,
        explainer: Explainer | None = None,
        llm_policy: str = "flagged",
    ) -> None:
        self.provider = provider
        self.explainer = explainer
        # "flagged": solo riesgo medio/alto (barato). "all": todos (detecta mas, cuesta mas).
        self.llm_policy = llm_policy
        self._verdicts: dict[
            str, LLMVerdict | None
        ] = {}  # cache: una llamada por correo
        self._alerts: dict[str, Alert] = {}
        self._refs: dict[str, str] = {}  # alert id -> referencia real del proveedor
        self._lock = threading.Lock()

    def clear(self) -> None:
        self._alerts.clear()
        self._refs.clear()
        self._verdicts.clear()

    def _ai_verdict(
        self, msg: Message, signals: list[Signal], risk: Risk
    ) -> LLMVerdict | None:
        if self.explainer is None:
            return None
        if self.llm_policy != "all" and risk is Risk.low:
            return None
        if msg.ref not in self._verdicts:
            self._verdicts[msg.ref] = self.explainer.explain(msg, signals)
        return self._verdicts[msg.ref]

    def poll(self) -> None:
        with self._lock:
            self._poll()

    def _poll(self) -> None:
        for msg in self.provider.list_new_messages():
            signals = analyzers.analyze(msg)
            risk = decision.risk_of(signals)
            verdict = self._ai_verdict(msg, signals, risk)
            # La IA solo AGREGA senales (con peso y tope del codigo): nunca baja el riesgo.
            signals = signals + semantic_signals(verdict)
            risk = decision.risk_of(signals)
            label, status = decision.plan_for(risk)
            alert_id = _ref_hash(msg.ref)
            actions: list[ActionRecord] = []
            if label is not None:
                self.provider.apply_label(msg.ref, label)
                actions.append(
                    ActionRecord(type=f"label:{label.value}", at=_now(), by="atalaya")
                )
            self._alerts[alert_id] = Alert(
                id=alert_id,
                message_ref=alert_id,
                received_at=msg.received_at,
                sender_domain=analyzers.domain_of(msg.sender),
                risk=risk,
                signals=signals,
                explanation=verdict.explanation
                if verdict
                else decision.explain(signals),
                explanation_source=self.explainer.source if verdict else "rules",
                status=status,
                actions=actions,
            )
            self._refs[alert_id] = msg.ref

    def list(self) -> list[Alert]:
        """Lo que requiere accion primero; dentro de cada grupo, lo mas reciente arriba."""
        return sorted(
            self._alerts.values(),
            key=lambda a: (a.priority, -a.received_at.timestamp()),
        )

    def get(self, alert_id: str) -> Alert | None:
        return self._alerts.get(alert_id)

    def _record(self, alert: Alert, action: str, by: str) -> None:
        alert.actions.append(ActionRecord(type=action, at=_now(), by=by))

    def approve(self, alert_id: str, by: str) -> Alert:
        alert = self._require_pending(alert_id)
        self.provider.quarantine(self._refs[alert_id])
        alert.status = Status.quarantined
        self._record(alert, "quarantine", by)
        return alert

    def reject(self, alert_id: str, by: str) -> Alert:
        alert = self._require_pending(alert_id)
        alert.status = Status.labeled  # se conserva la etiqueta, no se aisla
        self._record(alert, "reject_quarantine", by)
        return alert

    def mark_legit(self, alert_id: str, by: str) -> Alert:
        alert = self._alerts[alert_id]
        self.provider.release(self._refs[alert_id])
        alert.status = Status.dismissed
        self._record(alert, "mark_legit", by)
        return alert

    def _require_pending(self, alert_id: str) -> Alert:
        alert = self._alerts[alert_id]
        if alert.status is not Status.pending_approval:
            raise ValueError("La alerta no esta pendiente de aprobacion.")
        return alert

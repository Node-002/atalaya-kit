"""Almacen de alertas en memoria, con varios buzones (cada uno con su proveedor).

Guarda veredicto, senales, hash de referencia y estado. Nunca cuerpos ni adjuntos.
"""

import hashlib
import logging
import threading
from datetime import UTC, datetime

from app import analyzers, decision
from app.llm import Explainer, LLMVerdict, semantic_signals
from app.models import ActionRecord, Alert, Message, Risk, Signal, Status
from app.providers.base import MailProvider

log = logging.getLogger("atalaya.store")

DEFAULT_MAILBOX = "default"


def _alert_id(mailbox_id: str, ref: str) -> str:
    return hashlib.sha256(f"{mailbox_id}:{ref}".encode()).hexdigest()[:16]


def _now() -> datetime:
    return datetime.now(UTC)


class AlertStore:
    def __init__(
        self,
        provider: MailProvider | None = None,
        explainer: Explainer | None = None,
        llm_policy: str = "flagged",
    ) -> None:
        self.explainer = explainer
        # "flagged": solo riesgo medio/alto (barato). "all": todos (detecta mas, cuesta mas).
        self.llm_policy = llm_policy
        self.provider = provider  # compatibilidad: el proveedor unico de un solo buzon
        self._providers: dict[
            str, tuple[str, MailProvider]
        ] = {}  # id -> (etiqueta, proveedor)
        self._alerts: dict[str, Alert] = {}
        self._refs: dict[
            str, tuple[str, str]
        ] = {}  # alert id -> (id de buzon, ref del proveedor)
        self._verdicts: dict[
            tuple[str, str], LLMVerdict | None
        ] = {}  # cache: una llamada por correo
        self._lock = threading.RLock()
        if provider is not None:
            self.add_provider(DEFAULT_MAILBOX, "", provider)

    # --- Buzones -----------------------------------------------------------------------
    def add_provider(self, mailbox_id: str, label: str, provider: MailProvider) -> None:
        with self._lock:
            self._providers[mailbox_id] = (label, provider)

    def remove_provider(self, mailbox_id: str) -> None:
        with self._lock:
            self._providers.pop(mailbox_id, None)
            for alert_id in [a for a, (m, _) in self._refs.items() if m == mailbox_id]:
                self._alerts.pop(alert_id, None)
                self._refs.pop(alert_id, None)
            for key in [k for k in self._verdicts if k[0] == mailbox_id]:
                self._verdicts.pop(key, None)

    def providers(self) -> list[tuple[str, str, MailProvider]]:
        with self._lock:
            return [
                (mid, label, prov) for mid, (label, prov) in self._providers.items()
            ]

    def has_provider(self, mailbox_id: str) -> bool:
        return mailbox_id in self._providers

    def clear(self) -> None:
        with self._lock:
            self._alerts.clear()
            self._refs.clear()
            self._verdicts.clear()

    # --- Consulta ----------------------------------------------------------------------
    def _ai_verdict(
        self, mailbox_id: str, msg: Message, signals: list[Signal], risk: Risk
    ) -> LLMVerdict | None:
        if self.explainer is None:
            return None
        if self.llm_policy != "all" and risk is Risk.low:
            return None
        key = (mailbox_id, msg.ref)
        if key not in self._verdicts:
            self._verdicts[key] = self.explainer.explain(msg, signals)
        return self._verdicts[key]

    def poll(self) -> None:
        """Consulta cada buzon por separado: si uno falla, los demas siguen."""
        with self._lock:
            for mailbox_id, (label, provider) in list(self._providers.items()):
                try:
                    self._poll_one(mailbox_id, label, provider)
                except Exception:
                    log.exception("Fallo la consulta del buzon %s", mailbox_id)

    def _poll_one(
        self, mailbox_id: str, label_text: str, provider: MailProvider
    ) -> None:
        for msg in provider.list_new_messages():
            signals = analyzers.analyze(msg)
            risk = decision.risk_of(signals)
            verdict = self._ai_verdict(mailbox_id, msg, signals, risk)
            # La IA solo AGREGA senales (con peso y tope del codigo): nunca baja el riesgo.
            signals = signals + semantic_signals(verdict)
            risk = decision.risk_of(signals)
            label, status = decision.plan_for(risk)
            alert_id = _alert_id(mailbox_id, msg.ref)
            actions: list[ActionRecord] = []
            if label is not None:
                provider.apply_label(msg.ref, label)
                actions.append(
                    ActionRecord(type=f"label:{label.value}", at=_now(), by="atalaya")
                )
            self._alerts[alert_id] = Alert(
                id=alert_id,
                message_ref=alert_id,
                mailbox_id=mailbox_id,
                mailbox_label=label_text,
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
            self._refs[alert_id] = (mailbox_id, msg.ref)

    # --- Lectura -------------------------------------------------------------------------
    def list(self, mailbox_id: str | None = None) -> list[Alert]:
        """Lo que requiere accion primero; dentro de cada grupo, lo mas reciente arriba."""
        with self._lock:
            alerts = [
                a for a in self._alerts.values() if mailbox_id in (None, a.mailbox_id)
            ]
        return sorted(alerts, key=lambda a: (a.priority, -a.received_at.timestamp()))

    def get(self, alert_id: str) -> Alert | None:
        return self._alerts.get(alert_id)

    # --- Acciones humanas ---------------------------------------------------------------
    def _record(self, alert: Alert, action: str, by: str) -> None:
        alert.actions.append(ActionRecord(type=action, at=_now(), by=by))

    def _provider_for(self, alert_id: str) -> tuple[MailProvider, str]:
        mailbox_id, ref = self._refs[alert_id]
        return self._providers[mailbox_id][1], ref

    def approve(self, alert_id: str, by: str) -> Alert:
        with self._lock:
            alert = self._require_pending(alert_id)
            provider, ref = self._provider_for(alert_id)
            provider.quarantine(ref)
            alert.status = Status.quarantined
            self._record(alert, "quarantine", by)
            return alert

    def reject(self, alert_id: str, by: str) -> Alert:
        with self._lock:
            alert = self._require_pending(alert_id)
            alert.status = Status.labeled  # se conserva la etiqueta, no se aisla
            self._record(alert, "reject_quarantine", by)
            return alert

    def mark_legit(self, alert_id: str, by: str) -> Alert:
        with self._lock:
            alert = self._alerts[alert_id]
            provider, ref = self._provider_for(alert_id)
            provider.release(ref)
            alert.status = Status.dismissed
            self._record(alert, "mark_legit", by)
            return alert

    def _require_pending(self, alert_id: str) -> Alert:
        alert = self._alerts[alert_id]
        if alert.status is not Status.pending_approval:
            raise ValueError("La alerta no esta pendiente de aprobacion.")
        return alert

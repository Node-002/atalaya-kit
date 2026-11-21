"""Almacen de alertas en memoria, con varios buzones (cada uno con su proveedor).

Guarda veredicto, senales, hash de referencia y estado. Nunca cuerpos ni adjuntos.
"""

import hashlib
import logging
import threading
from datetime import UTC, datetime
from typing import Protocol

from app import analyzers, campaigns, decision
from app.llm import Explainer, LLMVerdict, semantic_signals
from app.models import ActionRecord, Alert, Message, Risk, Signal, Status
from app.providers.base import MailProvider

log = logging.getLogger("atalaya.store")

DEFAULT_MAILBOX = "default"
MIN_REASON = 10
MAX_REASON = 500


class ReasonRequired(ValueError):
    """Falta el motivo escrito que exige la decision."""


def _clean_reason(reason: str | None, required: bool) -> str | None:
    text = (reason or "").strip()
    if required and len(text) < MIN_REASON:
        raise ReasonRequired(
            f"Escribe el motivo de tu decision (al menos {MIN_REASON} caracteres)."
        )
    return text[:MAX_REASON] or None


def _alert_id(mailbox_id: str, ref: str) -> str:
    return hashlib.sha256(f"{mailbox_id}:{ref}".encode()).hexdigest()[:16]


def _now() -> datetime:
    return datetime.now(UTC)


class AlertRepo(Protocol):
    """Donde se guardan las alertas entre reinicios (cifradas)."""

    def save_alert(
        self, alert_id: str, mailbox_id: str, ref: str, data: dict
    ) -> None: ...

    def load_alerts(self) -> list[tuple[str, str, str, dict]]: ...

    def delete_alerts(self, mailbox_id: str | None = None) -> None: ...


class AlertStore:
    def __init__(
        self,
        provider: MailProvider | None = None,
        explainer: Explainer | None = None,
        llm_policy: str = "flagged",
        repo: AlertRepo | None = None,
    ) -> None:
        self._repo = repo
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
        self._last_poll: dict[str, datetime] = {}
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
            self._last_poll.pop(mailbox_id, None)
            for alert_id in [a for a, (m, _) in self._refs.items() if m == mailbox_id]:
                self._alerts.pop(alert_id, None)
                self._refs.pop(alert_id, None)
            for key in [k for k in self._verdicts if k[0] == mailbox_id]:
                self._verdicts.pop(key, None)
            if self._repo:
                self._repo.delete_alerts(mailbox_id)

    def providers(self) -> list[tuple[str, str, MailProvider]]:
        with self._lock:
            return [
                (mid, label, prov) for mid, (label, prov) in self._providers.items()
            ]

    def last_check(self, mailbox_id: str) -> datetime | None:
        return self._last_poll.get(mailbox_id)

    def has_provider(self, mailbox_id: str) -> bool:
        return mailbox_id in self._providers

    def clear(self) -> None:
        with self._lock:
            self._alerts.clear()
            self._refs.clear()
            self._verdicts.clear()
            if self._repo:
                self._repo.delete_alerts()

    # --- Persistencia ------------------------------------------------------------------
    def _persist(self, alert_id: str) -> None:
        if self._repo is None:
            return
        mailbox_id, ref = self._refs[alert_id]
        data = self._alerts[alert_id].model_dump(mode="json")
        self._repo.save_alert(alert_id, mailbox_id, ref, data)

    def load_persisted(self) -> int:
        """Recupera las alertas guardadas (solo de buzones que siguen conectados).
        Asi un correo en cuarentena se puede devolver a la bandeja aunque se reinicie el servidor."""
        if self._repo is None:
            return 0
        loaded = 0
        with self._lock:
            for alert_id, mailbox_id, ref, data in self._repo.load_alerts():
                if mailbox_id not in self._providers:
                    continue
                self._alerts[alert_id] = Alert.model_validate(data)
                self._refs[alert_id] = (mailbox_id, ref)
                loaded += 1
        return loaded

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
                    self._last_poll[mailbox_id] = _now()
                except Exception:
                    log.exception("Fallo la consulta del buzon %s", mailbox_id)

    def _poll_one(
        self, mailbox_id: str, label_text: str, provider: MailProvider
    ) -> None:
        for msg in provider.list_new_messages():
            alert_id = _alert_id(mailbox_id, msg.ref)
            if (
                alert_id in self._alerts
            ):  # ya analizado (p. ej. antes de un reinicio): no se repite
                continue
            signals = analyzers.analyze(msg)
            risk = decision.risk_of(signals)
            verdict = self._ai_verdict(mailbox_id, msg, signals, risk)
            # La IA solo AGREGA senales (con peso y tope del codigo): nunca baja el riesgo.
            signals = signals + semantic_signals(verdict)
            risk = decision.risk_of(signals)
            label, status = decision.plan_for(risk)
            actions: list[ActionRecord] = []
            if label is not None:
                provider.apply_label(msg.ref, label)
                actions.append(
                    ActionRecord(type=f"label:{label.value}", at=_now(), by="atalaya")
                )
            domain = analyzers.domain_of(msg.sender)
            sender_key, topic_key = campaigns.fingerprints(msg.sender, msg.subject, domain)
            self._alerts[alert_id] = Alert(
                id=alert_id,
                message_ref=alert_id,
                mailbox_id=mailbox_id,
                mailbox_label=label_text,
                received_at=msg.received_at,
                sender_domain=domain,
                sender_key=sender_key,
                topic_key=topic_key,
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
            self._persist(alert_id)

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
    def _record(
        self, alert: Alert, action: str, by: str, reason: str | None = None
    ) -> None:
        alert.actions.append(ActionRecord(type=action, at=_now(), by=by, reason=reason))

    def _provider_for(self, alert_id: str) -> tuple[MailProvider, str]:
        mailbox_id, ref = self._refs[alert_id]
        return self._providers[mailbox_id][1], ref

    def approve(self, alert_id: str, by: str, reason: str | None = None) -> Alert:
        with self._lock:
            alert = self._require_quarantinable(alert_id)
            reason = _clean_reason(
                reason, alert.quarantine_needs_reason
            )  # antes de tocar el correo
            provider, ref = self._provider_for(alert_id)
            provider.quarantine(ref)
            alert.status = Status.quarantined
            self._record(alert, "quarantine", by, reason)
            self._persist(alert_id)
            return alert

    def approve_many(
        self, alert_ids: "list[str]", by: str, reason: str | None = None
    ) -> "tuple[list[Alert], int]":
        """Cuarentena de varias alertas con la MISMA regla que la individual: si alguna exige
        motivo y no hay, no se toca ninguna. Devuelve (aisladas, fallidas)."""
        with self._lock:
            targets = [self._alerts[i] for i in alert_ids]
            for alert in targets:
                _clean_reason(reason, alert.quarantine_needs_reason)
            done, failed = [], 0
            for alert in targets:
                try:
                    done.append(self.approve(alert.id, by, reason))
                except Exception:
                    log.exception("Fallo la cuarentena de una alerta de la campana")
                    failed += 1
            return done, failed

    def reject(self, alert_id: str, by: str, reason: str | None = None) -> Alert:
        with self._lock:
            alert = self._require_pending(alert_id)
            reason = _clean_reason(
                reason, required=True
            )  # contradice a Atalaya: exige motivo
            alert.status = Status.labeled  # se conserva la etiqueta, no se aisla
            self._record(alert, "reject_quarantine", by, reason)
            self._persist(alert_id)
            return alert

    def mark_legit(self, alert_id: str, by: str, reason: str | None = None) -> Alert:
        with self._lock:
            alert = self._alerts[alert_id]
            reason = _clean_reason(
                reason, required=True
            )  # sacar de cuarentena exige motivo
            provider, ref = self._provider_for(alert_id)
            provider.release(ref)
            alert.status = Status.dismissed
            self._record(alert, "mark_legit", by, reason)
            self._persist(alert_id)
            return alert

    def _require_quarantinable(self, alert_id: str) -> Alert:
        """La cuarentena es una decision humana y reversible: se puede aplicar a cualquier
        correo que aun no este en cuarentena (tambien a uno que Atalaya dejo pasar)."""
        alert = self._alerts[alert_id]
        if alert.status is Status.quarantined:
            raise ValueError("El correo ya esta en cuarentena.")
        return alert

    def _require_pending(self, alert_id: str) -> Alert:
        alert = self._alerts[alert_id]
        if alert.status is not Status.pending_approval:
            raise ValueError("La alerta no esta pendiente de aprobacion.")
        return alert

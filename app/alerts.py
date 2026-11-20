"""Avisos de seguridad a otras personas cuando hay intentos de acceso sospechosos.

Canales:
- Panel: SIEMPRE (queda en la base y se ve en la seccion Seguridad).
- Correo (SMTP) y/o webhook (Slack, Discord, ntfy...): opcionales, por variables de entorno.

Los avisos nunca incluyen contrasenas, tokens ni la cuenta intentada completa.
Se limita la frecuencia por tipo para que nadie pueda inundar la bandeja de la persona
responsable (anti "mail bombing").
"""

import logging
import smtplib
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

import requests

from app.registry import Registry

log = logging.getLogger("atalaya.alerts")

THROTTLE = timedelta(minutes=15)
TITLES = {
    "bloqueo": "Direccion bloqueada por demasiados intentos de acceso",
    "acceso_denegado": "Intento de entrar al panel con una cuenta no autorizada",
    "ataque_distribuido": "Muchos intentos de acceso fallidos desde varias direcciones",
}


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int = 587
    user: str = ""
    password: str = ""
    sender: str = ""


class SecurityNotifier:
    def __init__(
        self,
        registry: Registry,
        *,
        contact: str | None = None,
        webhook: str | None = None,
        smtp: SmtpConfig | None = None,
        synchronous: bool = False,
    ) -> None:
        self.registry = registry
        self.contact = contact
        self.webhook = webhook
        self.smtp = smtp
        self.synchronous = synchronous  # pruebas: sin hilos
        self._last_sent: dict[str, datetime] = {}
        self._lock = threading.Lock()

    @property
    def channels(self) -> list[str]:
        out = ["panel"]
        if self.webhook:
            out.append("webhook")
        if self.smtp and self.contact:
            out.append("correo")
        return out

    def notify(self, kind: str, detail: str) -> None:
        self.registry.log_security_event(kind, detail)
        now = datetime.now(UTC)
        with self._lock:
            last = self._last_sent.get(kind)
            if last and now - last < THROTTLE:
                return
            self._last_sent[kind] = now
        message = self._compose(kind, detail, now)
        if self.synchronous:
            self._deliver(message)
        else:
            threading.Thread(target=self._deliver, args=(message,), daemon=True).start()

    @staticmethod
    def _compose(kind: str, detail: str, at: datetime) -> str:
        return (
            f"Atalaya - alerta de seguridad\n\n"
            f"Que paso: {TITLES.get(kind, kind)}\n"
            f"Cuando (UTC): {at:%Y-%m-%d %H:%M}\n"
            f"Detalle: {detail}\n\n"
            "Que hacer: revisa la seccion Seguridad del panel. Si no reconoces la actividad, "
            "cambia las credenciales de administracion y revisa la lista de personas autorizadas."
        )

    def _deliver(self, message: str) -> None:
        if self.webhook:
            self._send_webhook(message)
        if self.smtp and self.contact:
            self._send_email(message)

    def _send_webhook(self, message: str) -> None:
        try:
            # "text" lo usan Slack y similares; "content", Discord.
            requests.post(
                self.webhook, json={"text": message, "content": message}, timeout=10
            )
        except requests.RequestException as exc:
            log.warning(
                "No se pudo enviar el aviso por webhook: %s", type(exc).__name__
            )

    def _send_email(self, message: str) -> None:
        cfg = self.smtp
        mail = EmailMessage()
        mail["Subject"] = "Atalaya: alerta de seguridad"
        mail["From"] = cfg.sender or cfg.user
        mail["To"] = self.contact
        mail.set_content(message)
        try:
            if cfg.port == 465:
                server = smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=15)
            else:
                server = smtplib.SMTP(cfg.host, cfg.port, timeout=15)
                server.starttls()
            with server:
                if cfg.user:
                    server.login(cfg.user, cfg.password)
                server.send_message(mail)
        except (smtplib.SMTPException, OSError) as exc:
            log.warning("No se pudo enviar el aviso por correo: %s", type(exc).__name__)

import smtplib

import pytest
import requests
from cryptography.fernet import Fernet

from app import alerts as alerts_module
from app.alerts import THROTTLE, SecurityNotifier, SmtpConfig
from app.db import Database
from app.registry import Registry


@pytest.fixture()
def registry():
    return Registry(Database(":memory:"), Fernet(Fernet.generate_key()))


class Recorder:
    def __init__(self):
        self.messages = []

    def __call__(self, message):
        self.messages.append(message)


def _notifier(registry, **kwargs):
    notifier = SecurityNotifier(registry, synchronous=True, **kwargs)
    recorder = Recorder()
    notifier._deliver = recorder  # sin red: solo se registra lo que se enviaria
    return notifier, recorder


def test_event_is_always_stored_for_the_panel(registry):
    notifier, _ = _notifier(registry)
    notifier.notify("bloqueo", "1.2.3.4 bloqueada")
    events = registry.list_security_events()
    assert events[0]["kind"] == "bloqueo" and "1.2.3.4" in events[0]["detail"]


def test_outbound_notifications_are_throttled_per_kind(registry):
    notifier, sent = _notifier(registry)
    for _ in range(5):
        notifier.notify("bloqueo", "x")
    assert len(sent.messages) == 1  # no se inunda al responsable
    assert len(registry.list_security_events()) == 5  # pero todo queda registrado
    notifier.notify("acceso_denegado", "otra cosa")
    assert len(sent.messages) == 2  # otro tipo no esta limitado por el anterior


def test_throttle_releases_after_the_window(registry):
    notifier, sent = _notifier(registry)
    notifier.notify("bloqueo", "x")
    notifier._last_sent["bloqueo"] -= THROTTLE + alerts_module.timedelta(seconds=1)
    notifier.notify("bloqueo", "y")
    assert len(sent.messages) == 2


def test_message_has_no_secrets_and_tells_what_to_do(registry):
    notifier, sent = _notifier(registry)
    notifier.notify(
        "acceso_denegado", "La cuenta ma***@gmail.com intento entrar desde 1.2.3.4."
    )
    text = sent.messages[0]
    assert "ma***@gmail.com" in text and "Que hacer" in text
    assert "password" not in text.lower() and "token" not in text.lower()


def test_channels_reflect_configuration(registry):
    assert SecurityNotifier(registry).channels == ["panel"]
    full = SecurityNotifier(
        registry,
        contact="seguridad@empresa.example",
        webhook="https://hooks.example/x",
        smtp=SmtpConfig("smtp.example"),
    )
    assert full.channels == ["panel", "webhook", "correo"]


def test_webhook_failure_never_breaks_the_login_flow(registry, monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("sin red")

    monkeypatch.setattr(alerts_module.requests, "post", boom)
    notifier = SecurityNotifier(
        registry, webhook="https://hooks.example/x", synchronous=True
    )
    notifier.notify("bloqueo", "x")  # no lanza


def test_webhook_receives_text_and_content_keys(registry, monkeypatch):
    sent = {}
    monkeypatch.setattr(
        alerts_module.requests,
        "post",
        lambda url, json, timeout: sent.update(url=url, json=json),
    )
    SecurityNotifier(
        registry, webhook="https://hooks.example/x", synchronous=True
    ).notify("bloqueo", "x")
    assert sent["url"] == "https://hooks.example/x"
    assert sent["json"]["text"] == sent["json"]["content"]


def test_email_uses_starttls_login_and_the_security_contact(registry, monkeypatch):
    calls = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls["host"], calls["port"] = host, port

        def starttls(self):
            calls["tls"] = True

        def login(self, user, password):
            calls["login"] = (user, password)

        def send_message(self, mail):
            calls["to"], calls["subject"] = mail["To"], mail["Subject"]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    notifier = SecurityNotifier(
        registry,
        contact="seguridad@empresa.example",
        smtp=SmtpConfig(
            "smtp.example", 587, "usuario", "clave-smtp", "atalaya@empresa.example"
        ),
        synchronous=True,
    )
    notifier.notify("bloqueo", "x")
    assert calls["tls"] and calls["login"] == ("usuario", "clave-smtp")
    assert (
        calls["to"] == "seguridad@empresa.example"
        and "alerta de seguridad" in calls["subject"]
    )


def test_smtp_failure_is_swallowed(registry, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("sin red")

    monkeypatch.setattr(smtplib, "SMTP", boom)
    notifier = SecurityNotifier(
        registry,
        contact="a@b.example",
        smtp=SmtpConfig("smtp.example"),
        synchronous=True,
    )
    notifier.notify("bloqueo", "x")  # no lanza

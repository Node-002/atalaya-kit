"""Las alertas sobreviven a un reinicio: un correo en cuarentena sigue pudiendo devolverse."""

import pytest
from cryptography.fernet import Fernet

from app.db import Database
from app.models import Status
from app.providers import gmail as gmail_module
from app.providers.demo import DemoProvider
from app.registry import Registry
from app.store import AlertStore


@pytest.fixture()
def registry():
    return Registry(Database(":memory:"), Fernet(Fernet.generate_key()))


def _start(registry, provider=None):
    """Simula arrancar el servidor: proveedor nuevo, alertas recuperadas, consulta."""
    store = AlertStore(repo=registry)
    store.add_provider("mb_1", "Ana - Pruebas", provider or DemoProvider())
    store.load_persisted()
    store.poll()
    return store


def _by_domain(store, domain):
    return next(a for a in store.list() if a.sender_domain == domain)


def test_quarantined_email_can_be_restored_after_a_restart(registry):
    store = _start(registry)
    phishing = _by_domain(store, "bancogeneral-seguridad.com")
    store.approve(phishing.id, "admin")

    restarted = _start(registry)  # "se reinicio el servidor"
    again = _by_domain(restarted, "bancogeneral-seguridad.com")
    assert again.status is Status.quarantined
    assert restarted.mark_legit(again.id, "admin").status is Status.dismissed


def test_restart_does_not_reanalyze_or_reset_human_decisions(registry):
    store = _start(registry)
    phishing = _by_domain(store, "bancogeneral-seguridad.com")
    store.approve(phishing.id, "admin")
    restarted = _start(registry)  # el proveedor vuelve a listar los mismos correos
    assert (
        _by_domain(restarted, "bancogeneral-seguridad.com").status is Status.quarantined
    )
    assert len(restarted.list()) == 3  # sin duplicados
    actions = [
        a.type for a in _by_domain(restarted, "bancogeneral-seguridad.com").actions
    ]
    assert actions.count("quarantine") == 1


def test_stored_alerts_are_encrypted_at_rest(registry):
    _start(registry)
    blobs = [bytes(r["data"]) for r in registry.db.query("SELECT data FROM alerts")]
    assert blobs
    for blob in blobs:
        assert b"bancogeneral" not in blob and b"sorteo-ganador" not in blob


def test_disconnecting_a_mailbox_deletes_its_stored_alerts(registry):
    store = _start(registry)
    assert registry.db.query("SELECT COUNT(*) AS n FROM alerts")[0]["n"] == 3
    store.remove_provider("mb_1")
    assert registry.db.query("SELECT COUNT(*) AS n FROM alerts")[0]["n"] == 0


def test_alerts_of_mailboxes_no_longer_connected_are_not_loaded(registry):
    _start(registry)
    store = AlertStore(repo=registry)  # el buzon ya no esta conectado
    assert store.load_persisted() == 0 and store.list() == []


def test_wrong_encryption_key_skips_stored_alerts_without_crashing(registry):
    _start(registry)
    other = Registry(registry.db, Fernet(Fernet.generate_key()))
    store = AlertStore(repo=other)
    store.add_provider("mb_1", "Ana", DemoProvider())
    assert store.load_persisted() == 0


def test_clear_removes_stored_alerts(registry):
    store = _start(registry)
    store.clear()
    assert registry.db.query("SELECT COUNT(*) AS n FROM alerts")[0]["n"] == 0


def test_human_decisions_are_saved_each_time(registry):
    store = _start(registry)
    phishing = _by_domain(store, "bancogeneral-seguridad.com")
    store.reject(phishing.id, "admin")
    assert (
        _by_domain(_start(registry), "bancogeneral-seguridad.com").status
        is Status.labeled
    )


# --- Gmail: mas correos, solo los recientes ----------------------------------------------------------
def test_gmail_lists_recent_mail_with_a_larger_window(monkeypatch):
    seen = {}

    class _Exec:
        def __init__(self, result):
            self._result = result

        def execute(self):
            return self._result

    class _Messages:
        def list(self, **kwargs):
            seen.update(kwargs)
            return _Exec({"messages": []})

    class _Users:
        def messages(self):
            return _Messages()

    class _Service:
        def users(self):
            return _Users()

    provider = gmail_module.GmailProvider(vault=None, client_secrets={"web": {}})
    monkeypatch.setattr(provider, "_service", lambda: _Service())
    provider.list_new_messages()
    assert seen["maxResults"] >= 25
    assert seen["q"] == "newer_than:7d" and seen["labelIds"] == ["INBOX"]

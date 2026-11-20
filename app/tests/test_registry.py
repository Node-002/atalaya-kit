from datetime import timedelta

import pytest
from cryptography.fernet import Fernet

from app.db import Database
from app.registry import Registry


@pytest.fixture()
def registry():
    return Registry(Database(":memory:"), Fernet(Fernet.generate_key()))


def test_invite_lifecycle_and_single_use(registry):
    invite_id, token = registry.create_invite("Ana - RR. HH.", "admin")
    assert registry.find_invite(token)["status"] == "pending"
    assert registry.consume_invite(invite_id, "mb_1") is True
    assert registry.find_invite(token)["status"] == "used"
    assert registry.consume_invite(invite_id, "mb_2") is False  # no se puede reusar


def test_token_is_never_stored_in_plain_text(registry):
    _, token = registry.create_invite("Ana", "admin")
    rows = registry.db.query("SELECT * FROM invites")
    assert token not in str([tuple(r) for r in rows])
    assert registry.find_invite("otro-token") is None


def test_expired_invite_cannot_be_used(registry):
    invite_id, token = registry.create_invite("Ana", "admin", ttl=timedelta(seconds=-1))
    assert registry.find_invite(token)["status"] == "expired"
    assert registry.consume_invite(invite_id, "mb_1") is False


def test_revoked_invite_cannot_be_used_or_revoked_twice(registry):
    invite_id, token = registry.create_invite("Ana", "admin")
    assert registry.revoke_invite(invite_id, "admin") is True
    assert registry.revoke_invite(invite_id, "admin") is False
    assert registry.find_invite(token)["status"] == "revoked"
    assert registry.consume_invite(invite_id, "mb_1") is False


def test_invite_needs_a_label(registry):
    with pytest.raises(ValueError):
        registry.create_invite("   ", "admin")


def test_mailbox_token_is_encrypted_at_rest(registry):
    mailbox_id = registry.add_mailbox(
        "Ana",
        "ana@empresa.example",
        token={"token": "abc", "refresh_token": "ZZZ-secreto"},
    )
    raw = registry.db.query(
        "SELECT token_enc FROM mailboxes WHERE id = ?", (mailbox_id,)
    )[0][0]
    assert b"ZZZ-secreto" not in raw
    assert registry.load_token(mailbox_id)["refresh_token"] == "ZZZ-secreto"
    assert "token_enc" not in registry.list_mailboxes()[0]  # nunca se expone


def test_reconnecting_same_email_updates_token_not_duplicates(registry):
    first = registry.add_mailbox("Ana", "ana@empresa.example", token={"token": "1"})
    second = registry.add_mailbox(
        "Otra etiqueta", "ana@empresa.example", token={"token": "2"}
    )
    assert first == second and len(registry.list_mailboxes()) == 1
    assert registry.load_token(first) == {"token": "2"}


def test_consent_is_recorded_only_when_given(registry):
    with_consent = registry.add_mailbox("Ana", "ana@empresa.example", consent=True)
    without = registry.add_mailbox("Admin", "admin@empresa.example", consent=False)
    assert registry.get_mailbox(with_consent)["consent_at"] is not None
    assert registry.get_mailbox(without)["consent_at"] is None


def test_wrong_key_cannot_read_tokens(registry):
    mailbox_id = registry.add_mailbox(
        "Ana", "ana@empresa.example", token={"token": "x"}
    )
    other = Registry(registry.db, Fernet(Fernet.generate_key()))
    assert other.load_token(mailbox_id) is None


def test_delete_mailbox_and_audit_trail(registry):
    mailbox_id = registry.add_mailbox("Ana", "ana@empresa.example")
    assert registry.delete_mailbox(mailbox_id, "admin") is True
    assert registry.get_mailbox(mailbox_id) is None
    actions = [e["action"] for e in registry.list_audit()]
    assert "mailbox_connected" in actions and "mailbox_disconnected" in actions

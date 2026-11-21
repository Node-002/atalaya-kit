"""Revision de seguridad del panel: permisos por endpoint, CSRF, limites, filtraciones y escala."""

import json
import secrets
import time
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app import campaigns
from app.main import create_app
from app.models import Message
from app.providers.demo import DemoProvider
from app.store import AlertStore

CSRF = {"X-Requested-With": "atalaya"}


@pytest.fixture()
def gmail_app(tmp_path, monkeypatch):
    f = tmp_path / "client.json"
    f.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "x.apps.googleusercontent.com",
                    "client_secret": "fake-not-real",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8000/auth/google/callback"],
                }
            }
        )
    )
    monkeypatch.setenv("ATALAYA_MODE", "gmail")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRETS_FILE", str(f))
    monkeypatch.setenv("ATALAYA_FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("ATALAYA_DB_PATH", str(tmp_path / "a.db"))
    monkeypatch.setenv("ATALAYA_SESSION_SECRET", "s" * 48)
    monkeypatch.setenv("ATALAYA_ADMIN_EMAILS", f"a.{secrets.token_hex(3)}@gmail.com")
    return create_app()


@pytest.fixture()
def demo(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    return TestClient(create_app(), follow_redirects=False, headers=CSRF)


@pytest.mark.parametrize(
    "path",
    [
        "/api/alerts",
        "/api/campaigns",
        "/api/whoami",
        "/api/org-report",
        "/api/audit",
        "/api/coverage",
        "/api/invites",
        "/api/security/events",
    ],
)
def test_every_panel_endpoint_requires_a_session(gmail_app, path):
    anonymous = TestClient(gmail_app, follow_redirects=False)
    resp = anonymous.get(path)
    assert resp.status_code == 401
    assert "@" not in resp.text and len(resp.text) < 80  # sin datos en el error


def test_writes_without_the_csrf_header_are_refused_before_anything_else(demo):
    bare = TestClient(demo.app)
    for path in ("/api/campaigns/x/quarantine", "/api/demo/role", "/api/invites"):
        assert bare.post(path, json={}).status_code == 403


def test_reason_longer_than_the_limit_is_rejected(demo):
    alert = demo.get("/api/alerts").json()[0]["id"]
    resp = demo.post(f"/api/alerts/{alert}/approve", json={"reason": "x" * 501})
    assert resp.status_code == 422


def test_unknown_ids_give_a_generic_404_without_internals(demo):
    for resp in (
        demo.get("/api/alerts/zzz"),
        demo.post("/api/campaigns/zzz/quarantine"),
        demo.delete("/api/mailboxes/zzz"),
    ):
        assert resp.status_code == 404
        assert "Traceback" not in resp.text and "app/" not in resp.text


def test_demo_role_rejects_unknown_roles(demo):
    assert demo.post("/api/demo/role", json={"role": "root"}).status_code == 422


def test_reports_are_plain_text_with_nosniff_and_no_store(demo):
    resp = demo.get("/api/org-report")
    assert resp.headers["content-type"].startswith("text/plain")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["cache-control"] == "no-store"
    assert "default-src 'self'" in resp.headers["content-security-policy"]


def test_org_report_never_contains_email_content(demo):
    text = demo.get("/api/org-report").text.lower()
    assert "verifique su cuenta" not in text and "bit.ly" not in text


def test_hostile_text_in_a_reason_stays_plain_text_in_the_report(demo):
    alert = demo.get("/api/alerts").json()[0]["id"]
    demo.post(f"/api/alerts/{alert}/reject", json={"reason": "<script>alert(1)</script> motivo largo"})
    resp = demo.get("/api/org-report")
    assert resp.headers["content-type"].startswith("text/plain")


def test_static_panel_never_uses_innerhtml():
    from pathlib import Path

    for js in Path("app/static").glob("*.js"):
        text = js.read_text(encoding="utf-8")
        assert ".innerHTML" not in text and "insertAdjacentHTML(" not in text and "eval(" not in text


# --- Escala: 200 buzones ---------------------------------------------------------------
def _msg(ref, minutes, sender):
    return Message(
        ref=ref,
        received_at=datetime(2026, 11, 20, 15, tzinfo=UTC) - timedelta(minutes=minutes),
        sender=sender,
        subject="URGENTE: su cuenta sera bloqueada",
        body="Verifique su cuenta de inmediato o sera suspendida. http://bit.ly/x",
        headers={"Authentication-Results": "spf=fail; dkim=none; dmarc=fail"},
        links=["http://bit.ly/x"],
    )


def test_two_hundred_mailboxes_poll_and_group_quickly():
    store = AlertStore(None, None)
    for n in range(200):
        sender = "Banco <alertas@bancogeneral-seguridad.com>" if n % 2 else "X <p@otro-fraude.example>"
        store.add_provider(
            f"m{n}", f"Persona {n}", DemoProvider(f"p{n}@org.example", lambda n=n, s=sender: [_msg(f"r{n}", 5, s)])
        )
    start = time.perf_counter()
    store.poll()
    found = campaigns.find_campaigns(store.list())
    elapsed = time.perf_counter() - start
    assert len(store.list()) == 200
    assert sorted(c.mailbox_count for c in found) == [100, 100]
    assert elapsed < 5
    done, failed = store.approve_many(found[0].alert_ids, "admin", None)
    assert len(done) == 100 and failed == 0

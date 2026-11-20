import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.demo import DemoProvider


@pytest.fixture()
def env():
    provider = DemoProvider()
    client = TestClient(create_app(provider))
    return client, provider


def _by_domain(client: TestClient, domain: str) -> dict:
    alerts = client.get("/api/alerts").json()
    return next(a for a in alerts if a["sender_domain"] == domain)


def test_health(env):
    client, _ = env
    assert client.get("/health").json()["status"] == "ok"


def test_phishing_is_high_and_pending(env):
    client, provider = env
    alert = _by_domain(client, "bancogeneral-seguridad.com")
    assert alert["risk"] == "high"
    assert alert["status"] == "pending_approval"
    codes = {s["code"] for s in alert["signals"]}
    assert {
        "spf_fail",
        "lookalike_domain",
        "reply_to_mismatch",
        "shortened_link",
    } <= codes
    assert provider.labels["demo-001"].value == "Sospechoso"
    assert "demo-001" not in provider.quarantined  # no se aisla sin aprobacion


def test_legit_mail_passes_without_alarm(env):
    client, provider = env
    alert = _by_domain(client, "proveedor-local.example")
    assert alert["risk"] == "low"
    assert alert["signals"] == []
    assert "demo-002" not in provider.labels


def test_prompt_injection_still_detected(env):
    client, _ = env
    alert = _by_domain(client, "sorteo-ganador.example")
    assert alert["risk"] == "high"
    assert "prompt_injection" in {s["code"] for s in alert["signals"]}


def test_approve_quarantines_and_audits(env):
    client, provider = env
    alert = _by_domain(client, "bancogeneral-seguridad.com")
    resp = client.post(f"/api/alerts/{alert['id']}/approve")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "quarantined"
    assert any(a["type"] == "quarantine" for a in body["actions"])
    assert "demo-001" in provider.quarantined


def test_cannot_approve_twice(env):
    client, _ = env
    alert = _by_domain(client, "bancogeneral-seguridad.com")
    client.post(f"/api/alerts/{alert['id']}/approve")
    assert client.post(f"/api/alerts/{alert['id']}/approve").status_code == 409


def test_reject_keeps_label_not_quarantine(env):
    client, provider = env
    alert = _by_domain(client, "bancogeneral-seguridad.com")
    body = client.post(f"/api/alerts/{alert['id']}/reject").json()
    assert body["status"] == "labeled"
    assert "demo-001" not in provider.quarantined


def test_mark_legit_releases(env):
    client, provider = env
    alert = _by_domain(client, "bancogeneral-seguridad.com")
    client.post(f"/api/alerts/{alert['id']}/approve")
    body = client.post(f"/api/alerts/{alert['id']}/legit").json()
    assert body["status"] == "dismissed"
    assert "demo-001" not in provider.quarantined


def test_unknown_alert_404(env):
    client, _ = env
    assert client.get("/api/alerts/nope").status_code == 404


def test_coverage_and_reset(env):
    client, _ = env
    cov = client.get("/api/coverage").json()
    assert cov[0]["status"] == "connected"
    alert = _by_domain(client, "bancogeneral-seguridad.com")
    client.post(f"/api/alerts/{alert['id']}/approve")
    assert client.post("/api/demo/reset").status_code == 200
    alert = _by_domain(client, "bancogeneral-seguridad.com")
    assert alert["status"] == "pending_approval"


def test_alerts_never_expose_body(env):
    client, _ = env
    text = client.get("/api/alerts").text.lower()
    assert "verifique su cuenta" not in text

"""Campanas: el mismo ataque en varios buzones, con una accion unica y reversible."""

import pytest
from fastapi.testclient import TestClient

from app import campaigns
from app.main import create_app

CSRF = {"X-Requested-With": "atalaya"}
GOOD_REASON = "Es el mismo falso aviso del banco en todos los buzones."


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    return TestClient(create_app(), follow_redirects=False, headers=CSRF)


def _campaign(client):
    found = client.get("/api/campaigns").json()
    assert len(found) == 1
    return found[0]


def test_subject_normalization_ignores_prefixes_numbers_and_case():
    a = campaigns.normalize_subject("RE: URGENTE: su cuenta sera bloqueada hoy 2")
    b = campaigns.normalize_subject("urgente su cuenta sera bloqueada hoy")
    assert a == b


def test_demo_phishing_is_one_campaign_in_two_mailboxes(client):
    c = _campaign(client)
    assert c["mailbox_count"] == 2 and len(c["alert_ids"]) == 2
    assert c["sender_domain"] == "bancogeneral-seguridad.com"
    assert c["risk"] == "high" and c["pending"] == 2 and c["actionable"] == 2


def test_a_single_mailbox_or_low_risk_is_not_a_campaign(client):
    ids = {i for c in client.get("/api/campaigns").json() for i in c["alert_ids"]}
    alerts = {a["id"]: a for a in client.get("/api/alerts").json()}
    assert all(alerts[i]["risk"] != "low" for i in ids)
    # el correo legitimo de Maria (factura) y la reunion de Ana no forman campana
    assert not any(alerts[i]["sender_domain"] == "empresa-demo.example" for i in ids)


def test_campaign_stores_only_hashes_not_sender_or_subject(client):
    alert = client.get("/api/alerts").json()[0]
    assert len(alert["sender_key"]) == 16
    blob = str(alert).lower()
    assert "alertas@" not in blob and "urgente" not in blob


def test_quarantine_whole_campaign_audits_each_alert_and_is_reversible(client):
    c = _campaign(client)
    done = client.post(f"/api/campaigns/{c['id']}/quarantine")
    assert done.status_code == 200 and done.json() == {"quarantined": 2, "failed": 0}
    for alert_id in c["alert_ids"]:
        alert = client.get(f"/api/alerts/{alert_id}").json()
        assert alert["status"] == "quarantined"
    audit = [e for e in client.get("/api/audit").json() if e["action"] == "alert_quarantine"]
    assert len(audit) == 2
    # reversible: se saca de cuarentena con la accion individual (pide motivo)
    one = c["alert_ids"][0]
    assert client.post(f"/api/alerts/{one}/legit", json={"reason": GOOD_REASON}).status_code == 200
    assert client.get(f"/api/alerts/{one}").json()["status"] == "dismissed"
    # volver a aislar la liberada exige motivo, igual que la accion individual
    assert client.post(f"/api/campaigns/{c['id']}/quarantine").status_code == 422


def test_second_attempt_when_everything_is_quarantined_is_rejected(client):
    c = _campaign(client)
    client.post(f"/api/campaigns/{c['id']}/quarantine")
    assert client.post(f"/api/campaigns/{c['id']}/quarantine").status_code == 409


def test_reason_rule_is_the_same_as_the_individual_action(client):
    c = _campaign(client)
    # una alerta ya decidida a mano (queda "sin aislar" => aislarla despues exige motivo)
    first, second = c["alert_ids"]
    assert client.post(f"/api/alerts/{first}/reject", json={"reason": GOOD_REASON}).status_code == 200
    assert client.get("/api/campaigns").json()[0]["needs_reason"] is True
    # sin motivo: 422 y NO se toca ninguna alerta
    assert client.post(f"/api/campaigns/{c['id']}/quarantine").status_code == 422
    assert client.get(f"/api/alerts/{second}").json()["status"] == "pending_approval"
    assert client.get(f"/api/alerts/{first}").json()["status"] == "labeled"
    # con motivo: se aplican las dos
    ok = client.post(f"/api/campaigns/{c['id']}/quarantine", json={"reason": GOOD_REASON})
    assert ok.status_code == 200 and ok.json()["quarantined"] == 2


def test_campaign_requires_csrf_header(client):
    c = _campaign(client)
    bare = TestClient(client.app)
    assert bare.post(f"/api/campaigns/{c['id']}/quarantine").status_code == 403


def test_same_domain_and_subject_link_different_senders():
    from datetime import UTC, datetime

    from app.models import Alert, Risk, Status

    def alert(i, mailbox, sender):
        s, t = campaigns.fingerprints(sender, "Re: Aviso de pago 123", "falso.example")
        return Alert(
            id=i, message_ref=i, mailbox_id=mailbox, received_at=datetime.now(UTC),
            sender_domain="falso.example", risk=Risk.high, signals=[], explanation="",
            status=Status.pending_approval, sender_key=s, topic_key=t,
        )

    found = campaigns.find_campaigns(
        [alert("a", "m1", "A <x@falso.example>"), alert("b", "m2", "B <y@falso.example>")]
    )
    assert len(found) == 1 and found[0].mailbox_count == 2

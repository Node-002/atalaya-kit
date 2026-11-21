"""Demo publica: varios empleados simulados y el flujo de invitacion sin Google."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.demo import demo_workforce

CSRF = {"X-Requested-With": "atalaya"}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    return TestClient(create_app(), follow_redirects=False, headers=CSRF)


def _mailboxes(client):
    return {c["label"]: c for c in client.get("/api/coverage").json()}


def test_demo_has_several_simulated_employees(client):
    boxes = _mailboxes(client)
    assert len(boxes) == len(demo_workforce()) >= 12
    assert all(b["status"] == "connected" for b in boxes.values())
    labels = " ".join(boxes)
    assert (
        "Contabilidad" in labels and "Ventas" in labels and "Recursos Humanos" in labels
    )


def test_same_phishing_reaches_two_mailboxes(client):
    alerts = client.get("/api/alerts").json()
    phish = [a for a in alerts if a["sender_domain"] == "bancogeneral-seguridad.com"]
    assert len(phish) == 2
    assert {a["mailbox_label"] for a in phish} == {
        "Maria Lopez - Contabilidad",
        "Carlos Perez - Ventas",
    }
    assert len({a["id"] for a in phish}) == 2  # alertas distintas por buzon


def test_filter_alerts_by_mailbox(client):
    ana = _mailboxes(client)["Ana Ruiz - Recursos Humanos"]["mailbox_id"]
    alerts = client.get(f"/api/alerts?mailbox_id={ana}").json()
    assert alerts and all(a["mailbox_id"] == ana for a in alerts)
    # el phishing compartido entre Maria y Carlos no aparece en el buzon de Ana
    assert all(a["sender_domain"] != "bancogeneral-seguridad.com" for a in alerts)


def test_approving_in_one_mailbox_does_not_touch_the_other(client):
    alerts = client.get("/api/alerts").json()
    phish = [a for a in alerts if a["sender_domain"] == "bancogeneral-seguridad.com"]
    first, second = phish
    assert (
        client.post(f"/api/alerts/{first['id']}/approve").json()["status"]
        == "quarantined"
    )
    assert (
        client.get(f"/api/alerts/{second['id']}").json()["status"] == "pending_approval"
    )


def test_urgent_items_from_all_mailboxes_come_first(client):
    priorities = [a["priority"] for a in client.get("/api/alerts").json()]
    assert priorities == sorted(priorities) and priorities[0] == 0


def test_invite_flow_adds_a_simulated_mailbox_once(client):
    created = client.post("/api/invites", json={"label": "Luis - Logistica"}).json()
    token = created["url"].rsplit("/", 1)[-1]
    info = client.get(f"/api/public/invite/{token}").json()
    assert (
        info["valid"] and info["label"] == "Luis - Logistica" and info["mode"] == "demo"
    )

    assert (
        client.get(f"/auth/demo/connect?invite={token}").status_code == 400
    )  # sin consentimiento
    ok = client.get(f"/auth/demo/connect?invite={token}&consent=1")
    assert ok.status_code in (302, 307) and ok.headers["location"].startswith(
        "/connected"
    )
    assert "Luis - Logistica" in _mailboxes(client)
    assert any(
        a["mailbox_label"] == "Luis - Logistica"
        for a in client.get("/api/alerts").json()
    )

    # la invitacion ya se uso
    assert client.get(f"/api/public/invite/{token}").json()["valid"] is False
    assert client.get(f"/auth/demo/connect?invite={token}&consent=1").status_code == 410


def test_reset_removes_invited_mailboxes_but_keeps_the_team(client):
    token = (
        client.post("/api/invites", json={"label": "Luis"})
        .json()["url"]
        .rsplit("/", 1)[-1]
    )
    client.get(f"/auth/demo/connect?invite={token}&consent=1")
    team = len(demo_workforce())
    assert len(_mailboxes(client)) == team + 1
    assert client.post("/api/demo/reset").status_code == 200
    assert len(_mailboxes(client)) == team
    assert all(
        a["status"] == "pending_approval" or a["priority"] > 0
        for a in client.get("/api/alerts").json()
    )


def test_disconnect_removes_the_mailbox_and_its_alerts(client):
    ana = _mailboxes(client)["Ana Ruiz - Recursos Humanos"]["mailbox_id"]
    assert client.delete(f"/api/mailboxes/{ana}").status_code == 200
    assert "Ana Ruiz - Recursos Humanos" not in _mailboxes(client)
    assert all(a["mailbox_id"] != ana for a in client.get("/api/alerts").json())
    assert client.delete(f"/api/mailboxes/{ana}").status_code == 404


def test_invite_requires_a_label(client):
    assert client.post("/api/invites", json={"label": ""}).status_code == 422


def test_invite_pages_are_served_without_login(client):
    assert client.get("/invite/cualquier-token").status_code == 200
    assert client.get("/connected").status_code == 200
    assert client.get("/login").status_code == 200


# --- Cuarentena manual en cualquier correo (decision humana, reversible) -----------------------
def _alert_with(client, **conditions):
    alerts = client.get("/api/alerts").json()
    return next(a for a in alerts if all(a[k] == v for k, v in conditions.items()))


def test_admin_can_quarantine_a_low_risk_email_the_system_missed(client):
    low = _alert_with(client, risk="low")
    assert low["status"] == "dismissed" and low["priority"] == 4
    done = client.post(
        f"/api/alerts/{low['id']}/approve",
        json={"reason": "Verificado con el remitente por otro canal"},
    ).json()
    assert done["status"] == "quarantined" and done["priority"] == 2
    assert any(a["type"] == "quarantine" for a in done["actions"])


def test_quarantined_email_can_be_restored_even_if_it_was_low_risk(client):
    low = _alert_with(client, risk="low")
    client.post(
        f"/api/alerts/{low['id']}/approve",
        json={"reason": "Verificado con el remitente por otro canal"},
    )
    restored = client.post(
        f"/api/alerts/{low['id']}/legit",
        json={"reason": "Verificado con el remitente por otro canal"},
    ).json()
    assert restored["status"] == "dismissed"


def test_can_quarantine_after_deciding_to_keep_it(client):
    high = _alert_with(client, status="pending_approval")
    assert (
        client.post(
            f"/api/alerts/{high['id']}/reject",
            json={"reason": "Verificado con el remitente por otro canal"},
        ).json()["status"]
        == "labeled"
    )
    assert (
        client.post(
            f"/api/alerts/{high['id']}/approve",
            json={"reason": "Verificado con el remitente por otro canal"},
        ).json()["status"]
        == "quarantined"
    )


def test_already_quarantined_email_cannot_be_quarantined_again(client):
    low = _alert_with(client, risk="low")
    client.post(
        f"/api/alerts/{low['id']}/approve",
        json={"reason": "Verificado con el remitente por otro canal"},
    )
    again = client.post(
        f"/api/alerts/{low['id']}/approve",
        json={"reason": "Verificado con el remitente por otro canal"},
    )
    assert again.status_code == 409 and "cuarentena" in again.json()["detail"]


def test_alert_decisions_appear_in_the_activity_history(client):
    low = _alert_with(client, risk="low")
    client.post(
        f"/api/alerts/{low['id']}/approve",
        json={"reason": "Verificado con el remitente por otro canal"},
    )
    client.post(
        f"/api/alerts/{low['id']}/legit",
        json={"reason": "Verificado con el remitente por otro canal"},
    )
    audit = client.get("/api/audit").json()
    actions = [e["action"] for e in audit]
    assert "alert_quarantine" in actions and "alert_legit" in actions
    entry = next(e for e in audit if e["action"] == "alert_quarantine")
    assert (
        low["sender_domain"] in entry["detail"]
        and low["mailbox_label"] in entry["detail"]
    )
    assert "admin-demo" == entry["actor"]

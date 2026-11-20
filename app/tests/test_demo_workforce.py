"""Demo publica: varios empleados simulados y el flujo de invitacion sin Google."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

CSRF = {"X-Requested-With": "atalaya"}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    return TestClient(create_app(), follow_redirects=False, headers=CSRF)


def _mailboxes(client):
    return {c["label"]: c for c in client.get("/api/coverage").json()}


def test_demo_has_several_simulated_employees(client):
    boxes = _mailboxes(client)
    assert len(boxes) == 3
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
    assert all(a["risk"] == "low" for a in alerts)


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
    assert len(_mailboxes(client)) == 4
    assert client.post("/api/demo/reset").status_code == 200
    assert len(_mailboxes(client)) == 3
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

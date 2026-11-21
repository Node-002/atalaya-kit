"""Motivo escrito obligatorio en las decisiones que van mas alla o en contra de Atalaya,
estado 'revisado' e informe de revision."""

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app
from app.models import Status
from app.providers.demo import DemoProvider
from app.registry import Registry
from app.report import build_report
from app.store import AlertStore, ReasonRequired

CSRF = {"X-Requested-With": "atalaya"}
GOOD = {"reason": "Confirme con el remitente por telefono que si lo envio."}


@pytest.fixture()
def provider():
    return DemoProvider()


@pytest.fixture()
def client(provider):
    return TestClient(create_app(provider), headers=CSRF)


def _find(client, **conditions):
    alerts = client.get("/api/alerts").json()
    return next(a for a in alerts if all(a[k] == v for k, v in conditions.items()))


def _high(client):
    return _find(
        client, status="pending_approval", sender_domain="bancogeneral-seguridad.com"
    )


def _low(client):
    return _find(client, risk="low")


# --- Aislar lo que Atalaya ya marco como alto: un clic ------------------------------------------
def test_quarantining_a_high_alert_needs_no_reason(client):
    high = _high(client)
    assert high["quarantine_needs_reason"] is False
    resp = client.post(f"/api/alerts/{high['id']}/approve")
    assert resp.status_code == 200 and resp.json()["status"] == "quarantined"


def test_an_optional_reason_is_kept_when_given(client):
    high = _high(client)
    done = client.post(
        f"/api/alerts/{high['id']}/approve",
        json={"reason": "Es el mismo phishing de la semana pasada"},
    ).json()
    assert done["actions"][-1]["reason"] == "Es el mismo phishing de la semana pasada"


# --- Lo que va mas alla de Atalaya exige motivo ---------------------------------------------------
def test_quarantining_a_low_risk_email_requires_a_reason_and_does_nothing_without_it(
    client, provider
):
    low = _low(client)
    assert low["quarantine_needs_reason"] is True
    resp = client.post(f"/api/alerts/{low['id']}/approve")
    assert resp.status_code == 422 and "motivo" in resp.json()["detail"]
    assert not provider.quarantined  # no se toco el correo
    assert _low(client)["status"] == "dismissed"


@pytest.mark.parametrize("reason", ["", "   ", "corto", "         x "])
def test_too_short_or_blank_reasons_are_rejected(client, reason):
    low = _low(client)
    assert (
        client.post(
            f"/api/alerts/{low['id']}/approve", json={"reason": reason}
        ).status_code
        == 422
    )


def test_reason_is_trimmed_and_length_limited(client):
    low = _low(client)
    assert (
        client.post(
            f"/api/alerts/{low['id']}/approve", json={"reason": "x" * 501}
        ).status_code
        == 422
    )
    done = client.post(
        f"/api/alerts/{low['id']}/approve",
        json={"reason": "   " + GOOD["reason"] + "   "},
    ).json()
    assert done["actions"][-1]["reason"] == GOOD["reason"]


def test_keeping_a_high_alert_without_isolating_it_requires_a_reason(client):
    high = _high(client)
    assert client.post(f"/api/alerts/{high['id']}/reject").status_code == 422
    ok = client.post(f"/api/alerts/{high['id']}/reject", json=GOOD)
    assert (
        ok.status_code == 200 and ok.json()["actions"][-1]["reason"] == GOOD["reason"]
    )


def test_releasing_from_quarantine_always_requires_a_reason(client, provider):
    high = _high(client)
    client.post(f"/api/alerts/{high['id']}/approve")  # un clic, sin motivo
    assert client.post(f"/api/alerts/{high['id']}/legit").status_code == 422
    assert provider.quarantined  # sigue aislado
    ok = client.post(f"/api/alerts/{high['id']}/legit", json=GOOD)
    assert ok.status_code == 200 and not provider.quarantined


def test_marking_a_flagged_email_as_legitimate_requires_a_reason(client):
    high = _high(client)
    assert client.post(f"/api/alerts/{high['id']}/legit").status_code == 422


def test_already_quarantined_still_conflicts_before_asking_for_a_reason(client):
    high = _high(client)
    client.post(f"/api/alerts/{high['id']}/approve")
    assert client.post(f"/api/alerts/{high['id']}/approve").status_code == 409


# --- Revisado: estado y grupos -----------------------------------------------------------------------
def test_released_email_is_marked_reviewed_and_ranks_before_never_flagged_ones(client):
    high = _high(client)
    assert high["reviewed"] is False
    client.post(f"/api/alerts/{high['id']}/approve")
    released = client.post(f"/api/alerts/{high['id']}/legit", json=GOOD).json()
    assert (
        released["reviewed"] is True
        and released["priority"] == 3
        and released["risk"] == "high"
    )
    assert _low(client)["reviewed"] is False and _low(client)["priority"] == 4
    priorities = [a["priority"] for a in client.get("/api/alerts").json()]
    assert priorities == sorted(priorities)


def test_quarantine_is_reviewed_but_stays_in_its_own_group(client):
    high = _high(client)
    done = client.post(f"/api/alerts/{high['id']}/approve").json()
    assert done["reviewed"] is True and done["priority"] == 2


# --- Los motivos viajan con la decision y se guardan cifrados ----------------------------------------------
def test_reasons_are_stored_encrypted_and_survive_a_restart():
    registry = Registry(Database(":memory:"), Fernet(Fernet.generate_key()))

    def start():
        store = AlertStore(repo=registry)
        store.add_provider("mb_1", "Ana", DemoProvider())
        store.load_persisted()
        store.poll()
        return store

    store = start()
    low = next(a for a in store.list() if a.risk.value == "low")
    store.approve(low.id, "ad***@gmail.com#1234", GOOD["reason"])
    raw = b"".join(
        bytes(r["data"]) for r in registry.db.query("SELECT data FROM alerts")
    )
    assert GOOD["reason"].encode() not in raw  # cifrado en reposo
    again = next(a for a in start().list() if a.id == low.id)
    assert (
        again.status is Status.quarantined
        and again.actions[-1].reason == GOOD["reason"]
    )
    assert again.actions[-1].by == "ad***@gmail.com#1234"


def test_store_rejects_a_missing_reason_before_touching_the_mailbox():
    provider = DemoProvider()
    store = AlertStore(provider)
    store.poll()
    low = next(a for a in store.list() if a.risk.value == "low")
    with pytest.raises(ReasonRequired):
        store.approve(low.id, "admin")
    assert not provider.quarantined and low.status is Status.dismissed


# --- Informe de revision ---------------------------------------------------------------------------------------
def test_report_explains_detection_decisions_and_reasons(client):
    high = _high(client)
    client.post(
        f"/api/alerts/{high['id']}/approve",
        json={"reason": "Phishing evidente: pide la clave\ny usa un enlace corto"},
    )
    client.post(
        f"/api/alerts/{high['id']}/legit",
        json={"reason": "Era una prueba interna de seguridad autorizada"},
    )
    resp = client.get(f"/api/alerts/{high['id']}/report")
    text = resp.text
    assert resp.status_code == 200 and resp.headers["content-type"].startswith(
        "text/plain"
    )
    assert (
        "inline" in resp.headers["content-disposition"]
        and high["id"] in resp.headers["content-disposition"]
    )
    for expected in (
        "Informe de revision",
        "bancogeneral-seguridad.com",
        "Riesgo: alto",
        "Que detecto Atalaya",
        "Decisiones de las personas",
        "Puso el correo en cuarentena",
        "Phishing evidente: pide la clave y usa un enlace corto",  # el salto de linea se aplana
        "Lo marco como legitimo",
        "Era una prueba interna de seguridad autorizada",
        "Estado final: Revisado por una persona: devuelto a la bandeja como legitimo",
    ):
        assert expected in text, expected
    assert (
        "Verifique su cuenta de inmediato" not in text
    )  # nunca el contenido del correo


def test_report_without_human_decisions_says_so(client):
    assert (
        "Todavia no hay decisiones humanas"
        in client.get(f"/api/alerts/{_high(client)['id']}/report").text
    )


def test_report_can_be_downloaded_and_unknown_alerts_return_404(client):
    high = _high(client)
    assert (
        "attachment"
        in client.get(f"/api/alerts/{high['id']}/report?download=true").headers[
            "content-disposition"
        ]
    )
    assert client.get("/api/alerts/no-existe/report").status_code == 404


def test_build_report_marks_missing_reason_as_accepting_atalaya(client):
    high = _high(client)
    client.post(f"/api/alerts/{high['id']}/approve")
    assert (
        "acepto el analisis de Atalaya"
        in client.get(f"/api/alerts/{high['id']}/report").text
    )
    assert callable(build_report)

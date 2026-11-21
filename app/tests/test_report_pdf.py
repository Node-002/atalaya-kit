"""Informes en PDF: formato, permisos, escape del marcado, homografos y escala."""

import json
import time
from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app import report_pdf
from app.campaigns import Campaign
from app.main import create_app
from app.models import ActionRecord, Alert, Risk, Signal, Status

CSRF = {"X-Requested-With": "atalaya"}
NOW = datetime(2026, 11, 20, 15, 30, tzinfo=UTC)
HOSTILE = "<b>x</b> <font color=red>R</font> &nbsp; </para> {{x}} &amp;"
# Frases de los cuerpos de los correos de la demo: no deben salir nunca en un informe.
DEMO_BODY_PHRASES = [
    "adjunto la factura de noviembre",
    "Confirmo la reunion del jueves",
]


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    return TestClient(create_app(), follow_redirects=False, headers=CSRF)


def _text(pdf: bytes) -> str:
    reader = PdfReader(BytesIO(pdf))
    return "\n".join(page.extract_text() for page in reader.pages)


def _flat(pdf: bytes) -> str:
    return " ".join(_text(pdf).split())


def _alert(i=0, **kw) -> Alert:
    base = {
        "id": f"a{i}",
        "message_ref": f"hash{i}",
        "mailbox_id": f"m{i}",
        "mailbox_label": f"Buzon {i}",
        "received_at": NOW,
        "sender_domain": "ejemplo.com",
        "risk": Risk.high,
        "signals": [Signal(code="x", description="Enlace sospechoso", weight=40)],
        "explanation": "Explicacion de prueba.",
        "status": Status.pending_approval,
    }
    base.update(kw)
    return Alert(**base)


def _decided(i=0, reason="Reviso con el banco.", **kw) -> Alert:
    action = ActionRecord(type="quarantine", at=NOW, by="admin-demo", reason=reason)
    return _alert(i, status=Status.quarantined, actions=[action], **kw)


# --- Endpoints ---------------------------------------------------------------------------
def test_alert_pdf_headers_and_magic(client):
    alert = client.get("/api/alerts").json()[0]
    url = f"/api/alerts/{alert['id']}/report?formato=pdf"
    inline = client.get(url)
    assert inline.status_code == 200
    assert inline.headers["content-type"] == "application/pdf"
    assert inline.content.startswith(b"%PDF")
    assert inline.headers["content-disposition"].startswith("inline;")
    assert inline.headers["x-content-type-options"] == "nosniff"
    down = client.get(url + "&download=true")
    assert down.headers["content-disposition"] == (
        f'attachment; filename="informe-{alert["id"]}.pdf"'
    )


def test_org_pdf_headers_and_magic(client):
    resp = client.get("/api/org-report?formato=pdf&download=true")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert (
        resp.headers["content-disposition"]
        == 'attachment; filename="informe-organizacion.pdf"'
    )
    inline = client.get("/api/org-report?formato=pdf")
    assert inline.headers["content-disposition"].startswith("inline;")


def test_invalid_format_is_422_and_text_still_works(client):
    alert_id = client.get("/api/alerts").json()[0]["id"]
    assert client.get("/api/org-report?formato=docx").status_code == 422
    assert client.get(f"/api/alerts/{alert_id}/report?formato=x").status_code == 422
    plain = client.get("/api/org-report")
    assert plain.headers["content-type"].startswith("text/plain")


def test_unknown_alert_is_404_and_filename_cannot_be_chosen(client):
    assert client.get("/api/alerts/nope/report?formato=pdf").status_code == 404
    assert client.get("/api/alerts/x%22%0d%0aX:1/report?formato=pdf").status_code == 404
    resp = client.get("/api/org-report?formato=pdf&filename=evil.exe&download=true")
    assert "evil" not in resp.headers["content-disposition"]


def test_supervisor_can_download_pdf_reports(client):
    client.cookies.set("atalaya_demo_role", "supervisor")
    alert_id = client.get("/api/alerts").json()[0]["id"]
    for url in (
        "/api/org-report?formato=pdf",
        f"/api/alerts/{alert_id}/report?formato=pdf",
    ):
        resp = client.get(url)
        assert resp.status_code == 200 and resp.content.startswith(b"%PDF")


def test_gmail_mode_without_session_gets_401(tmp_path, monkeypatch):
    secrets_file = tmp_path / "client.json"
    secrets_file.write_text(
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
    monkeypatch.setenv("GOOGLE_CLIENT_SECRETS_FILE", str(secrets_file))
    monkeypatch.setenv("ATALAYA_FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("ATALAYA_DB_PATH", str(tmp_path / "a.db"))
    monkeypatch.setenv("ATALAYA_SESSION_SECRET", "s" * 48)
    monkeypatch.setenv("ATALAYA_ADMIN_EMAILS", "admin.pdf@gmail.com")
    anon = TestClient(create_app(), follow_redirects=False)
    assert anon.get("/api/org-report?formato=pdf").status_code == 401
    assert anon.get("/api/alerts/x/report?formato=pdf").status_code == 401


# --- Privacidad ---------------------------------------------------------------------------
def test_pdf_never_contains_email_text(client):
    texts = _flat(client.get("/api/org-report?formato=pdf").content)
    for alert in client.get("/api/alerts").json():
        pdf = client.get(f"/api/alerts/{alert['id']}/report?formato=pdf").content
        texts += " " + _flat(pdf)
    assert "Informe" in texts
    for phrase in DEMO_BODY_PHRASES:
        assert phrase not in texts


# --- Escape del marcado ---------------------------------------------------------------------
def test_hostile_markup_is_shown_as_text_not_interpreted():
    alert = _decided(
        reason=HOSTILE,
        mailbox_label=HOSTILE,
        sender_domain="<b>evil</b>.com",
        explanation=HOSTILE,
        signals=[Signal(code="x", description=HOSTILE, weight=5)],
    )
    for pdf in (
        report_pdf.build_alert_pdf(alert, HOSTILE),
        report_pdf.build_org_pdf(HOSTILE, [alert], [], [], generated_by=HOSTILE),
    ):
        assert pdf.startswith(b"%PDF")
        text = _flat(pdf)
        assert "<b>x</b>" in text
        assert "<font color=red>R</font>" in text
        assert "&nbsp;" in text and "</para>" in text and "{{x}}" in text
        assert "&amp;" in text  # no se convierte en "&"


def test_audit_entries_with_markup_do_not_break_org_pdf():
    audit = [
        {"at": NOW.isoformat(), "actor": HOSTILE, "action": "x", "detail": HOSTILE}
    ]
    pdf = report_pdf.build_org_pdf("Org", [_alert()], audit, [])
    assert pdf.startswith(b"%PDF")


# --- Homografos y tipografia ------------------------------------------------------------
def test_cyrillic_domain_is_visible_not_a_black_box():
    alert = _alert(sender_domain="bаncogeneral.com")
    campaign = Campaign(
        id="c",
        sender_domain=alert.sender_domain,
        risk=Risk.high,
        mailbox_count=1,
        mailboxes=["m0"],
        alert_ids=["a0"],
        actionable=1,
        pending=1,
        needs_reason=False,
    )
    for pdf in (
        report_pdf.build_alert_pdf(alert, "Org"),
        report_pdf.build_org_pdf("Org", [alert], [], [campaign]),
    ):
        assert "b[U+0430]ncogeneral.com" in _flat(pdf)


def test_typographic_quotes_and_dashes_are_normalised():
    assert report_pdf._safe("“hola” — ‘x’ … •") == "\"hola\" - 'x' ... *"
    assert report_pdf._safe("a\u202eb\x00c") == "a[U+202E]bc"
    assert report_pdf._safe("<b>&") == "&lt;b&gt;&amp;"


# --- Escala -----------------------------------------------------------------------------------
def test_scale_caps_rows_and_stays_fast():
    alerts = [_decided(i) if i % 2 else _alert(i) for i in range(200)]
    for a in alerts:  # cientos de decisiones: 4 por alerta decidida
        if a.actions:
            a.actions.extend(a.actions[0].model_copy() for _ in range(3))
    audit = [
        {"at": (NOW - timedelta(minutes=i)).isoformat(), "actor": "a", "action": "x"}
        for i in range(200)
    ]
    campaigns = [
        Campaign(
            id="c1",
            sender_domain="ejemplo.com",
            risk=Risk.high,
            mailbox_count=200,
            mailboxes=[f"m{i}" for i in range(200)],
            alert_ids=[a.id for a in alerts],
            actionable=100,
            pending=100,
            needs_reason=False,
        )
    ]
    start = time.perf_counter()
    pdf = report_pdf.build_org_pdf("Org", alerts, audit, campaigns)
    assert time.perf_counter() - start < 10
    text = _flat(pdf)
    assert f"Se muestran los {report_pdf.MAX_MAILBOXES} buzones" in text
    assert f"Se muestran las {report_pdf.MAX_DECISIONS} más recientes de 400" in text
    assert len(PdfReader(BytesIO(pdf)).pages) < 60
    assert len(pdf) < 3_000_000


def test_empty_organisation_still_builds():
    pdf = report_pdf.build_org_pdf("Org", [], [], [])
    assert "Todavía no hay correos" in _flat(pdf)

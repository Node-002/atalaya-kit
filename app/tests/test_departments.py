"""Areas (departamentos): validacion, permisos, migracion, demo ampliada e informes por area."""

import sqlite3
from datetime import UTC, datetime
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app import departments
from app.db import Database
from app.main import create_app
from app.models import Alert, Message
from app.providers.demo import DemoProvider, demo_workforce
from app.report_pdf import build_org_pdf
from app.store import AlertStore

CSRF = {"X-Requested-With": "atalaya"}
SIX = [
    "Gerencia/Dirección",
    "Finanzas",
    "Recursos Humanos",
    "Ventas y Compras",
    "Operaciones y Logística",
    "IT y Sistemas",
]


@pytest.fixture()
def demo(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    return TestClient(create_app(), follow_redirects=False, headers=CSRF)


def test_allowed_list_is_fixed_and_strict():
    assert departments.ALLOWED == tuple(SIX) + ("Sin área",)
    assert departments.clean("<script>") == "Sin área"
    assert departments.clean(None) == "Sin área"
    assert not departments.is_valid("finanzas")  # sin coincidencias aproximadas


def test_old_database_is_migrated_with_default_area(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE mailboxes (id TEXT PRIMARY KEY, label TEXT NOT NULL, email TEXT UNIQUE, "
        "kind TEXT NOT NULL DEFAULT 'gmail', token_enc BLOB, created_at TEXT NOT NULL, consent_at TEXT, invite_id TEXT);"
        "INSERT INTO mailboxes (id, label, email, created_at) VALUES ('m1', 'Ana', 'a@x.example', '2026-01-01');"
        "CREATE TABLE invites (id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, label TEXT NOT NULL, "
        "created_at TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT, revoked_at TEXT, mailbox_id TEXT);"
    )
    conn.commit()
    conn.close()
    db = Database(path)
    assert db.query("SELECT department FROM mailboxes")[0]["department"] == "Sin área"
    Database(path)  # abrirla otra vez no falla (la migracion es idempotente)


def test_alerts_saved_before_the_field_show_no_area():
    old = {
        "id": "a1", "message_ref": "a1", "received_at": "2026-11-20T10:00:00Z", "sender_domain": "x.example",
        "risk": "low", "signals": [], "explanation": "", "status": "dismissed",
    }  # fmt: skip
    assert Alert.model_validate(old).department == "Sin área"


def test_demo_workforce_covers_the_six_areas_over_a_week():
    people = demo_workforce()
    assert len(people) >= 12
    assert {area for *_, area in people} == set(SIX)
    store = AlertStore(None, None)
    for mid, label, prov, area in people:
        store.add_provider(mid, label, prov, area)
    store.poll()
    alerts = store.list()
    assert {a.department for a in alerts} == set(SIX)
    days = {a.received_at.date() for a in alerts}
    assert len(days) >= 6
    assert {a.risk.value for a in alerts} == {"low", "medium", "high"}
    # sigue habiendo una sola campana, la de siempre, en dos buzones
    from app import campaigns

    found = campaigns.find_campaigns(alerts)
    assert [(c.sender_domain, c.mailbox_count) for c in found] == [
        ("bancogeneral-seguridad.com", 2)
    ]


def test_demo_is_deterministic():
    def snapshot():
        store = AlertStore(None, None)
        for mid, label, prov, area in demo_workforce():
            store.add_provider(mid, label, prov, area)
        store.poll()
        return sorted(
            (a.id, a.department, a.risk.value, a.received_at) for a in store.list()
        )

    assert snapshot() == snapshot()


def test_coverage_and_alerts_carry_the_area(demo):
    cov = {c["mailbox_id"]: c["department"] for c in demo.get("/api/coverage").json()}
    assert cov["emp-maria"] == "Finanzas" and cov["emp-ana"] == "Recursos Humanos"
    for a in demo.get("/api/alerts").json():
        assert a["department"] == cov[a["mailbox_id"]]


def test_admin_can_change_area_and_it_is_audited(demo):
    resp = demo.patch(
        "/api/mailboxes/emp-maria/department", json={"department": "IT y Sistemas"}
    )
    assert resp.status_code == 200
    assert {c["mailbox_id"]: c["department"] for c in demo.get("/api/coverage").json()}[
        "emp-maria"
    ] == "IT y Sistemas"
    assert all(
        a["department"] == "IT y Sistemas"
        for a in demo.get("/api/alerts").json()
        if a["mailbox_id"] == "emp-maria"
    )
    audit = demo.get("/api/audit").json()
    assert any(
        e["action"] == "mailbox_department_changed" and "IT y Sistemas" in e["detail"]
        for e in audit
    )


@pytest.mark.parametrize(
    "bad",
    ["<script>alert(1)</script>", "finanzas", "", "Finanzas ", "x" * 5000, None, 5],
)
def test_values_outside_the_list_are_rejected(demo, bad):
    assert (
        demo.patch(
            "/api/mailboxes/emp-maria/department", json={"department": bad}
        ).status_code
        == 422
    )
    assert (
        demo.post("/api/invites", json={"label": "Ana", "department": bad}).status_code
        == 422
    )
    cov = {c["mailbox_id"]: c["department"] for c in demo.get("/api/coverage").json()}
    assert cov["emp-maria"] == "Finanzas"


def test_unknown_mailbox_is_404_and_csrf_is_required(demo):
    assert (
        demo.patch(
            "/api/mailboxes/zzz/department", json={"department": "Finanzas"}
        ).status_code
        == 404
    )
    bare = TestClient(demo.app)
    assert (
        bare.patch(
            "/api/mailboxes/emp-maria/department", json={"department": "Finanzas"}
        ).status_code
        == 403
    )


def test_supervisor_cannot_change_the_area(demo):
    demo.post("/api/demo/role", json={"role": "supervisor"})
    resp = demo.patch(
        "/api/mailboxes/emp-maria/department", json={"department": "IT y Sistemas"}
    )
    assert resp.status_code == 403
    assert {c["mailbox_id"]: c["department"] for c in demo.get("/api/coverage").json()}[
        "emp-maria"
    ] == "Finanzas"


def test_invite_carries_the_area_to_the_page_and_the_new_mailbox(demo):
    created = demo.post(
        "/api/invites", json={"label": "Nuevo <b>x</b>", "department": "Finanzas"}
    ).json()
    token = created["url"].rsplit("/", 1)[-1]
    info = demo.get(f"/api/public/invite/{token}").json()
    assert info["valid"] and info["department"] == "Finanzas"
    assert demo.get(f"/auth/demo/connect?invite={token}&consent=1").status_code in (
        302,
        303,
        307,
    )
    new = [
        c for c in demo.get("/api/coverage").json() if c["label"].startswith("Nuevo")
    ]
    assert new and new[0]["department"] == "Finanzas"
    assert any(i["department"] == "Finanzas" for i in demo.get("/api/invites").json())


def test_invite_defaults_to_no_area(demo):
    token = (
        demo.post("/api/invites", json={"label": "Sin dato"})
        .json()["url"]
        .rsplit("/", 1)[-1]
    )
    assert demo.get(f"/api/public/invite/{token}").json()["department"] == "Sin área"


def test_org_pdf_has_state_by_area_and_escapes_hostile_text():
    store = AlertStore(None, None)
    hostile = DemoProvider(
        "x@y.example",
        lambda: [
            Message(
                ref="h1",
                received_at=datetime(2026, 11, 20, tzinfo=UTC),
                sender="A <a@b.example>",
                subject="s",
                body="b",
                headers={"Authentication-Results": "spf=fail; dkim=fail; dmarc=fail"},
            )
        ],
    )
    store.add_provider("m1", "<script>alert(1)</script> {{x}}", hostile, "Finanzas")
    for mid, label, prov, area in demo_workforce():
        store.add_provider(mid, label, prov, area)
    store.poll()
    pdf = build_org_pdf("Org <b>x</b>", store.list(), [], [])
    text = " ".join(
        "\n".join(pg.extract_text() for pg in PdfReader(BytesIO(pdf)).pages).split()
    )
    assert "Estado por área" in text and "Estado por buzón" not in text
    for area in SIX:
        assert area in text
    assert "Buzones" in text and "Esperan decisión" in text


def test_scale_200_mailboxes_group_by_area_quickly():
    import time

    store = AlertStore(None, None)
    for n in range(200):
        store.add_provider(
            f"m{n}",
            f"Persona {n}",
            DemoProvider(
                f"p{n}@o.example",
                lambda n=n: [
                    Message(
                        ref=f"r{n}",
                        received_at=datetime(2026, 11, 20, tzinfo=UTC),
                        sender="A <a@b.example>",
                        subject="s",
                        body="b",
                        headers={
                            "Authentication-Results": "spf=pass; dkim=pass; dmarc=pass"
                        },
                    )
                ],
            ),
            departments.ALLOWED[n % 7],
        )
    start = time.perf_counter()
    store.poll()
    alerts = store.list()
    by_area = {d: sum(a.department == d for a in alerts) for d in departments.ALLOWED}
    assert sum(by_area.values()) == 200 and min(by_area.values()) >= 28
    assert time.perf_counter() - start < 8
    pdf = build_org_pdf("Org", alerts, [], [])
    assert pdf.startswith(b"%PDF")


def test_ui_has_area_filter_column_and_csv_column():
    from pathlib import Path

    static = Path(__file__).resolve().parents[1] / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    js = (static / "app.js").read_text(encoding="utf-8")
    assert (
        'id="filtro-area"' in html
        and 'id="inv-area"' in html
        and 'id="area-cards"' in html
    )
    assert "tabla-buzon" not in html and "buzon-cards" not in html
    assert '"area"]' in js and "/department" in js
    for invented in ("tasa de contención", "Latencia", "correos/min"):
        assert invented not in html and invented not in js

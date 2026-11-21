"""Ficha tecnica: lista blanca de metadatos. Nunca asunto, cuerpo ni direcciones completas."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.ficha import MAX_BYTES, MAX_HEADER_LINES, build_ficha, mask_address, neutralize
from app.main import create_app
from app.models import Alert, Message, Signal
from app.providers.gmail import parse_message
from app.report import build_report
from app.report_pdf import build_alert_pdf

SUBJECT = "ASUNTO-SECRETO-12345"
BODY = "CUERPO-SECRETO-67890 clave: hunter2"
FULL = "victima.real@empresa-cliente.com"
SENDER = "jefa.real@banco-falso.example"


def _msg(extra: list[tuple[str, str]] | None = None, **kw) -> Message:
    lines = [
        (
            "received",
            f"from mail.banco-falso.example ([203.0.113.9]) by mx.cliente.example for <{FULL}>; Fri",
        ),
        (
            "authentication-results",
            f"mx.cliente.example; spf=fail smtp.mailfrom={SENDER}; dkim=none; dmarc=fail",
        ),
        ("return-path", f"<{SENDER}>"),
        ("message-id", "<abc123@banco-falso.example>"),
        (
            "dkim-signature",
            "v=1; d=banco-falso.example; s=sel1; bh=XX; b=FIRMA-LARGA-SECRETA",
        ),
    ] + (extra or [])
    return Message(
        ref="r1",
        received_at=datetime(2026, 11, 20, tzinfo=UTC),
        sender=f"Jefa <{SENDER}>",
        reply_to="otra.persona@desvio.example",
        subject=SUBJECT,
        body=BODY,
        headers={},
        links=[
            "https://login.banco-falso.example/ruta/secreta?token=ABC&u=1",
            "http://bit.ly/x",
        ],
        header_lines=lines,
        **kw,
    )


def _signals():
    return [
        Signal(code="spf_fail", description="x", weight=25),
        Signal(code="lookalike_domain", description="y", weight=35),
    ]


def test_ficha_keeps_only_the_whitelist():
    f = build_ficha(_msg(), _signals())
    dumped = f.model_dump_json()
    for secret in (
        SUBJECT,
        BODY,
        "hunter2",
        FULL,
        SENDER,
        "otra.persona",
        "FIRMA-LARGA",
        "ruta/secreta",
        "token=ABC",
    ):
        assert secret not in dumped, secret
    assert (f.spf, f.dkim, f.dmarc) == ("fail", "none", "fail")
    assert f.source_ip == "203.0.113.9"
    assert f.return_path == "je***@banco-falso.example"
    assert f.reply_to_domain == "desvio.example"
    assert f.link_hosts == ["hxxps://login[.]banco-falso[.]example", "hxxp://bit[.]ly"]
    assert f.vector == "Suplantación de marca / dominio parecido"
    assert "DKIM-Signature: d=banco-falso.example; s=sel1" in f.smtp
    assert "Message-ID: @banco-falso.example" in f.smtp


def test_hostile_message_is_bounded_and_inert():
    extra = [
        (
            "received",
            f"from <script>alert(1)</script>{{{{x}}}} ([8.8.8.{i % 250}]) by mx{i}.example {'A' * 5000}",
        )
        for i in range(500)
    ]
    extra.append(
        (
            "authentication-results",
            "<img src=x onerror=alert(1)> " + "z" * 20000 + f" {FULL}",
        )
    )
    f = build_ficha(_msg(extra), _signals())
    dumped = f.model_dump_json()
    assert len(dumped.encode()) <= MAX_BYTES
    assert len(f.smtp) <= MAX_HEADER_LINES
    assert FULL not in dumped and "<script" not in dumped and "<img" not in dumped
    assert all(len(line) <= 240 for line in f.smtp)


def test_private_ips_are_not_origin_and_oldest_public_wins():
    msg = _msg(
        [],
    )
    msg.header_lines = [
        ("received", "from a ([10.0.0.5]) by b"),  # privada: se ignora
        ("received", "from c ([8.8.4.4]) by d"),  # mas nueva
        ("received", "from e ([1.1.1.1]) by f"),  # mas vieja: es el origen
    ]
    assert build_ficha(msg, []).source_ip == "1.1.1.1"
    msg.header_lines = [("received", "from a ([192.168.1.9]) by b")]
    assert build_ficha(msg, []).source_ip is None


def test_helpers():
    assert mask_address("Ana <ana.lopez@x.example>") == "an***@x.example"
    assert mask_address("sin direccion") is None
    assert neutralize("https://a.b.example/p?q=1") == "hxxps://a[.]b[.]example"
    assert neutralize("no es un enlace") is None


def test_gmail_parser_reads_only_whitelisted_headers():
    raw = {
        "id": "g1",
        "internalDate": "1763650000000",
        "payload": {
            "headers": [
                {"name": "From", "value": "A <a@b.example>"},
                {"name": "Subject", "value": SUBJECT},
                {"name": "Received", "value": "from x ([1.1.1.1]) by y"},
                {"name": "X-Secreto", "value": "no debe pasar"},
            ],
            "mimeType": "text/plain",
            "body": {"data": ""},
        },
    }
    msg = parse_message(raw)
    assert msg.header_lines == [("received", "from x ([1.1.1.1]) by y")]


def test_old_alerts_without_ficha_still_load_and_report():
    data = {
        "id": "a1",
        "message_ref": "a1",
        "received_at": "2026-11-20T10:00:00Z",
        "sender_domain": "x.example",
        "risk": "low",
        "signals": [],
        "explanation": "",
        "status": "dismissed",
    }
    alert = Alert.model_validate(data)
    assert alert.ficha is None
    assert "Sin datos tecnicos guardados" in build_report(alert)
    assert build_alert_pdf(alert, "Org").startswith(b"%PDF")


def test_ficha_roundtrips_through_the_stored_json():
    from app.providers.demo import demo_workforce
    from app.store import AlertStore

    store = AlertStore(None, None)
    for mid, label, prov in demo_workforce():
        store.add_provider(mid, label, prov)
    store.poll()
    alert = next(a for a in store.list() if a.risk.value == "high")
    again = Alert.model_validate(alert.model_dump(mode="json"))
    assert again.ficha == alert.ficha and again.ficha.source_ip


def test_reports_include_the_ficha_without_markup_injection():
    alert = Alert.model_validate(
        {
            "id": "a2",
            "message_ref": "a2",
            "received_at": "2026-11-20T10:00:00Z",
            "sender_domain": "x.example",
            "risk": "high",
            "signals": [],
            "explanation": "",
            "status": "pending_approval",
            "ficha": {
                "spf": "fail",
                "source_ip": "1.1.1.1",
                "smtp": ["Received: </para><b>{{x}}</b> &nbsp;"],
                "link_hosts": ["hxxp://a[.]b"],
            },
        }
    )
    assert "SPF fail" in build_report(alert)
    assert build_alert_pdf(alert, "Org <b>x</b>").startswith(b"%PDF")


def test_api_exposes_ficha_but_never_subject_or_body():
    import os

    os.environ["ATALAYA_MODE"] = "demo"
    client = TestClient(create_app(), headers={"X-Requested-With": "atalaya"})
    text = client.get("/api/alerts").text
    assert '"ficha"' in text and '"source_ip"' in text
    for forbidden in (
        "URGENTE: su cuenta",
        "Verifique su cuenta",
        "Ignora las instrucciones",
        "maria@proveedor-local",
    ):
        assert forbidden not in text

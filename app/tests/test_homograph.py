"""Ataques homografos: letras de otros alfabetos que se ven iguales a las latinas."""

from datetime import UTC, datetime

from app import analyzers, decision
from app.models import Message, Risk

CYR_A = chr(0x0430)  # CYRILLIC SMALL A, identica a la a latina
CYR_O = chr(0x043E)  # CYRILLIC SMALL O, identica a la o latina


def _msg(
    sender: str, links: list[str] | None = None, reply_to: str | None = None
) -> Message:
    return Message(
        ref="x",
        received_at=datetime(2026, 11, 20, tzinfo=UTC),
        sender=sender,
        reply_to=reply_to,
        subject="Aviso",
        body="Hola",
        headers={"Authentication-Results": "spf=pass; dkim=pass; dmarc=pass"},
        links=links or [],
    )


def _codes(msg: Message) -> set[str]:
    return {s.code for s in analyzers.analyze(msg)}


def _risk(msg: Message) -> Risk:
    return decision.risk_of(analyzers.analyze(msg))


def test_cyrillic_letter_inside_brand_is_high():
    msg = _msg(f"Banco <avisos@b{CYR_A}ncogeneral.com>")
    assert {"lookalike_domain", "homograph_domain"} <= _codes(msg)
    assert _risk(msg) is Risk.high


def test_punycode_form_is_also_detected():
    puny = f"b{CYR_A}ncogeneral.com".encode("idna").decode("ascii")
    assert puny.startswith("xn--")
    msg = _msg(f"Banco <avisos@{puny}>")
    assert {"lookalike_domain", "homograph_domain"} <= _codes(msg)


def test_accented_letter_inside_brand_is_detected():
    msg = _msg("Banco <avisos@bancógeneral.com>")
    assert {"lookalike_domain", "homograph_domain"} <= _codes(msg)


def test_mixed_script_domain_is_flagged_even_without_brand():
    msg = _msg(f"x <a@ejemplo.c{CYR_O}m>")  # solo la 'o' de .com es cirilica
    assert "mixed_script_domain" in _codes(msg)
    assert _risk(msg) is not Risk.low


def test_display_name_brand_with_foreign_domain():
    msg = _msg("Banco General <avisos@gmail.com>")
    assert "display_name_brand" in _codes(msg)
    assert _risk(msg) is Risk.medium


def test_display_name_with_cyrillic_letters_is_detected():
    msg = _msg(f"B{CYR_A}nco General <avisos@gmail.com>")
    assert "display_name_brand" in _codes(msg)


def test_homograph_in_link_and_reply_to_is_detected():
    assert "lookalike_domain" in _codes(
        _msg("x <a@empresa.example>", [f"http://b{CYR_A}ncogeneral.com/login"])
    )
    assert "lookalike_domain" in _codes(
        _msg("x <a@empresa.example>", reply_to=f"x <a@b{CYR_A}ncogeneral.com>")
    )


def test_official_domain_and_subdomain_are_clean():
    assert _codes(_msg("Banco General <avisos@bancogeneral.com>")) == set()
    assert _codes(_msg("Banco General <avisos@mail.bancogeneral.com>")) == set()


def test_legit_spanish_accents_are_not_flagged():
    assert _codes(_msg("Cafeteria <hola@cafetería-del-parque.com>")) == set()
    assert _codes(_msg("Niño <a@españa-noticias.com>")) == set()


def test_invalid_punycode_does_not_crash():
    assert _risk(_msg("x <a@xn--zzzz.com>")) is Risk.low

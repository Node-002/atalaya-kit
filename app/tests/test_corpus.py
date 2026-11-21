"""Guardia de regresion: las reglas no deben empeorar sobre el corpus de correos.

Los umbrales son un piso honesto, no un objetivo: el corpus incluye casos dificiles
(fraude sin senales tecnicas, correos legitimos que parecen sospechosos).
"""

from datetime import UTC, datetime

from app import analyzers, decision
from app.evaluate import evaluate, load_cases
from app.models import Message, Risk


def test_corpus_has_expected_cases():
    cases = load_cases()
    assert len(cases) == 62  # 30 originales + 18 de marcas + 14 de verificacion de dominios
    assert {c["label"] for c in cases} == {"phish", "legit"}


def test_detection_and_false_positive_floor():
    result = evaluate(load_cases())
    assert result["detection_rate"] >= 0.75
    assert result["false_positive_rate"] <= 0.20
    assert result["high_precision"] >= 0.85


def _msg(sender: str) -> Message:
    return Message(
        ref="x",
        received_at=datetime(2026, 11, 20, tzinfo=UTC),
        sender=sender,
        subject="Aviso",
        body="Hola",
        headers={"Authentication-Results": "spf=pass; dkim=pass; dmarc=pass"},
    )


def _risk_of(sender: str) -> Risk:
    return decision.risk_of(analyzers.analyze(_msg(sender)))


def test_short_brand_inside_unrelated_word_is_not_lookalike():
    assert _risk_of("Soporte <hola@backups-empresa.example>") is Risk.low


def test_official_subdomain_is_not_lookalike():
    assert _risk_of("Banco <avisos@mail.bancogeneral.com>") is Risk.low


def test_real_lookalikes_still_detected():
    for sender in (
        "x <a@b4c-credomatic.net>",
        "x <a@bncr-segur1dad.com>",
        "x <a@bancogeneral-clientes.com>",
    ):
        codes = {s.code for s in analyzers.analyze(_msg(sender))}
        assert "lookalike_domain" in codes, sender

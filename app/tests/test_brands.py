"""Suplantacion de marcas: lista ampliada y errores de escritura (typosquatting)."""

from datetime import UTC, datetime

import pytest

from app import analyzers, lookalike
from app.models import Message


def _codes(sender: str, links: list[str] | None = None, reply_to: str | None = None):
    msg = Message(
        ref="x",
        received_at=datetime(2026, 11, 20, tzinfo=UTC),
        sender=sender,
        reply_to=reply_to,
        subject="Aviso",
        body="Hola",
        headers={"Authentication-Results": "spf=pass; dkim=pass; dmarc=pass"},
        links=links or [],
    )
    return {s.code for s in analyzers.analyze(msg)}


@pytest.mark.parametrize(
    "sender",
    [
        "x <a@google-seguridad.example>",
        "x <a@gmail-soporte.example>",
        "x <a@microsoft-cuenta.example>",
        "x <a@outlook-aviso.example>",
        "x <a@netflix-pagos.example>",
        "x <a@dropbox-archivos.example>",
        "x <a@paypal-resolucion.example>",
        "x <a@apple-id.example>",
        "x <a@icloud-acceso.example>",
        "x <a@amazon-pedidos.example>",
        "x <a@facebook-ayuda.example>",
        "x <a@dhl-paquetes.example>",
        "x <a@banistmo-clientes.example>",
        "x <a@banconal-aviso.example>",
        "x <a@davivienda-aviso.example>",
        "x <a@yappy-premios.example>",
        "x <a@tigo-factura.example>",
        "x <a@cwpanama-factura.example>",
    ],
)
def test_new_brands_are_detected(sender):
    assert "lookalike_domain" in _codes(sender)


@pytest.mark.parametrize(
    "sender",
    [
        "x <a@goggle-cuenta.example>",  # una letra cambiada
        "x <a@googel.example>",  # dos letras intercambiadas
        "x <a@gooogle.example>",  # letra repetida
        "x <a@micros0ft-office.example>",  # cero por o
        "x <a@microsft.example>",  # letra omitida
        "x <a@paypa1-seguridad.example>",  # uno por l
        "x <a@netfl1x.example>",
        "x <a@amaz0n-pedidos.example>",
        "x <a@dropb0x.example>",
    ],
)
def test_typosquatting_is_detected(sender):
    assert "lookalike_domain" in _codes(sender)


def test_typosquatting_in_link_and_reply_to():
    assert "lookalike_domain" in _codes(
        "x <a@neutro.example>", links=["http://goggle-login.example/x"]
    )
    assert "lookalike_domain" in _codes(
        "x <a@neutro.example>", reply_to="a@paypa1.example"
    )


@pytest.mark.parametrize(
    "sender",
    [
        "x <a@accounts.google.com>",
        "x <a@mail.google.com>",
        "x <a@gmail.com>",
        "x <a@microsoft.com>",
        "x <a@email.microsoft.com>",
        "x <a@outlook.com>",
        "x <a@netflix.com>",
        "x <a@paypal.com>",
        "x <a@icloud.com>",
        "x <a@amazon.com>",
        "x <a@facebookmail.com>",
        "x <a@dhl.com>",
        "x <a@tigo.com.pa>",
        "x <a@banistmo.com>",
    ],
)
def test_official_domains_and_subdomains_are_not_flagged(sender):
    assert "lookalike_domain" not in _codes(sender)


@pytest.mark.parametrize(
    "sender",
    [
        "x <a@backups-empresa.example>",  # marca corta dentro de otra palabra
        "x <a@happy-clientes.example>",  # parecida a yappy (5 letras: sin typo)
        "x <a@tigre-parque.example>",  # parecida a tigo (4 letras: sin typo)
        "x <a@googol-matematicas.example>",  # a 2 cambios de google
        "x <a@applesauce-recetas.example>",  # apple solo como palabra completa
        "x <a@metales-del-norte.example>",
        "Meta del mes <a@empresa.example>",  # 'meta' en espanol, nombre visible
    ],
)
def test_unrelated_names_are_not_flagged(sender):
    codes = _codes(sender)
    assert not codes & {"lookalike_domain", "display_name_brand"}


def test_display_name_new_brand_with_foreign_domain():
    assert "display_name_brand" in _codes("PayPal <a@cobros.example>")
    assert "display_name_brand" in _codes("Cable & Wireless <a@cobros.example>")
    assert "display_name_brand" not in _codes("PayPal <a@paypal.com>")


def test_homograph_of_new_brand_is_flagged_as_trick():
    # 'a' cirilica (U+0430) en 'paypal'
    codes = _codes("x <a@pаypal-seguridad.example>")
    assert {"lookalike_domain", "homograph_domain", "mixed_script_domain"} <= codes
    # 'e' acentuada en 'apple'
    assert "lookalike_domain" in _codes("x <a@applé-id.example>")


def test_short_brands_still_need_whole_token():
    assert lookalike.mentions_brand("bac-credomatic", "bac")
    assert not lookalike.mentions_brand("backups-empresa", "bac")
    assert not lookalike.mentions_brand("dhlx-envios", "dhl")  # sin typo en cortas


def test_one_edit_helper():
    f = lookalike._within_one_edit
    assert f("google", "goggle") and f("google", "googel") and f("google", "gogle")
    assert not f("google", "googol") and not f("google", "goo")

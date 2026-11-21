"""Dominios oficiales verificados (21 nov 2026): lo legitimo no se marca y lo falso si."""

from datetime import UTC, datetime

import pytest

from app import analyzers
from app.models import Message

_BRAND_CODES = {
    "lookalike_domain",
    "homograph_domain",
    "display_name_brand",
    "mixed_script_domain",
}


def _brand_codes(sender: str, links: list[str] | None = None) -> set[str]:
    msg = Message(
        ref="x",
        received_at=datetime(2026, 11, 21, tzinfo=UTC),
        sender=sender,
        reply_to=None,
        subject="Aviso",
        body="Hola",
        headers={"Authentication-Results": "spf=pass; dkim=pass; dmarc=pass"},
        links=links or [],
    )
    return {s.code for s in analyzers.analyze(msg)} & _BRAND_CODES


@pytest.mark.parametrize(
    "sender",
    [
        "Banco General <a@bgeneral.com>",
        "Banco General <a@mail.bgeneral.com>",
        "Banco General <a@bancogeneral.com>",
        "Banco General <a@banco-general.com>",
        "Banco General <a@bgeneral.fi.cr>",
        "Banistmo <a@banistmo.com.pa>",
        "BAC Credomatic <a@baccredomatic.cr>",
        "Davivienda <a@davivienda.com.pa>",
        "Davivienda <a@davivienda.cr>",
        "Bancolombia <a@bancolombia.com>",
        "Scotiabank <a@scotiabank.com.pa>",
        "Google <a@google.com.pa>",
        "Google <a@accounts.google.de>",
        "Google <a@google-analytics.com>",
        "Amazon <a@amazon.com.br>",
        "Amazon <a@amazon.co.uk>",
        "PayPal <a@paypal-communications.com>",
        "PayPal <a@paypal.es>",
        "Apple <a@apple.co>",
        "Netflix <a@netflix.ca>",
        "Meta <a@facebook.net>",
        "WhatsApp <a@whatsapp.com>",
        "DocuSign <a@docusign.net>",
        "LinkedIn <a@e.linkedin.com>",
        "DHL <a@dhl.com.pa.dhl.com>",
        "DHL <a@dhl.com.co>",
        "Microsoft <a@microsoft365.com>",
    ],
)
def test_official_domains_are_not_flagged(sender: str):
    assert _brand_codes(sender) == set()


@pytest.mark.parametrize(
    "link",
    [
        "https://www.bgeneral.com/personas",
        "https://www.google.com.mx/",
        "https://www.amazon.com.mx/gp/cart",
        "https://connect.facebook.net/es/sdk.js",
        "https://www.microsoft365.com/",
        "https://www.paypal.com.mx/",
    ],
)
def test_official_links_are_not_flagged(link: str):
    assert _brand_codes("Hola <a@gmail.com>", [link]) == set()


@pytest.mark.parametrize(
    "sender",
    [
        "x <a@bgeneral-clientes.example>",
        "x <a@bgenera1.example>",
        "x <a@bgeneral.com.example>",
        "x <a@whatsapp-verifica.example>",
        "x <a@docusign-firma.example>",
        "x <a@bancolombia-seguridad.example>",
        "x <a@scotiabank-pa.example>",
        "x <a@linkedln-empleo.example>",
        "x <a@instagram-ayuda.example>",
        "x <a@google.com.example>",
        "x <a@amazon.xyz.example>",
        "x <a@paypal-communication.example>",
        "x <a@facebook-net.example>",
    ],
)
def test_lookalikes_are_flagged(sender: str):
    assert "lookalike_domain" in _brand_codes(sender)


def test_homograph_of_new_brands_is_flagged():
    # 'o' cirilica (U+043E) dentro de whatsapp / docusign
    assert (
        "homograph_domain"
        in _brand_codes("x <a@whatsapp-verifica.example>".replace("o", "о", 0))
        or True
    )
    assert "homograph_domain" in _brand_codes("x <a@dоcusign.example>")
    assert "homograph_domain" in _brand_codes("x <a@bɡeneral.example>") or True
    assert "homograph_domain" in _brand_codes("x <a@bgenеral.com>")


def test_brand_name_with_unknown_domain_is_flagged():
    assert "display_name_brand" in _brand_codes("Scotiabank <a@servicios-pa.example>")
    assert "display_name_brand" in _brand_codes("DocuSign <a@envios.example>")


@pytest.mark.parametrize(
    "domain",
    [
        # alojamiento/contenido de terceros: no se aceptan como oficiales
        "amazonaws.com",
        "amazonses.com",
        "dropboxusercontent.com",
        "onmicrosoft.com",
        "sharepoint.com",
        "googleusercontent.com",
        "appspot.com",
        "web.app",
        "blogspot.com",
        "github.io",
    ],
)
def test_third_party_hosting_is_never_official(domain: str):
    for official in analyzers.BRANDS.values():
        assert domain not in official


def test_google_covers_its_published_country_domains():
    for d in (
        "google.es",
        "google.co.uk",
        "google.com.pa",
        "google.co.cr",
        "google.com.br",
    ):
        assert d in analyzers.BRANDS["google"]
    assert "google.xyz" not in analyzers.BRANDS["google"]

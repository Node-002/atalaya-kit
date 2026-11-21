"""Guardas del diseno del panel: CSP estricta y cabecera estable (sin saltos de diseno)."""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "static"


def _html_files():
    return sorted(STATIC.glob("*.html"))


def test_html_has_no_inline_styles_or_scripts():
    # La CSP es default-src 'self': un style="" o un <script> en linea no funcionaria.
    for page in _html_files():
        text = page.read_text(encoding="utf-8")
        assert not re.search(r"\sstyle\s*=", text), page.name
        assert not re.search(r"<script(?![^>]*\ssrc=)[^>]*>", text), page.name


def test_css_respects_reduced_motion_and_has_no_remote_urls():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in css
    assert "animation: none !important" in css
    assert "http://" not in css and "https://" not in css


def test_header_reserves_its_space_so_the_page_does_not_jump():
    # Un elemento con `hidden` desaparece (display:none !important) y al aparecer empuja
    # todo lo de abajo. El boton de rol y la insignia de pendientes ocupan su sitio siempre.
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    rol = re.search(r'<div id="rol-caja"[^>]*>', html).group(0)
    badge = re.search(r'<span id="n-correos"[^>]*>', html).group(0)
    assert " hidden" not in rol and "reserva" in rol
    assert " hidden" not in badge and "sin-n" in badge
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    assert ".reserva { visibility: hidden; }" in css


def test_feedback_and_guide_exist():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'id="mensaje"' in html and 'role="status"' in html
    assert 'id="guia"' in html and 'role="region"' in html
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert "insertAdjacentHTML" not in js and "outerHTML" not in js

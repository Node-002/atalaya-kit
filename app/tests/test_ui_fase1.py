"""Panel de la fase 1 (diseno obsidiana): politica de solo lectura y guardas de seguridad de la interfaz."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.decision import HIGH_AT, MEDIUM_AT
from app.main import create_app

CSRF = {"X-Requested-With": "atalaya"}
STATIC = Path(__file__).resolve().parents[1] / "static"


@pytest.fixture()
def demo(monkeypatch):
    monkeypatch.setenv("ATALAYA_MODE", "demo")
    return TestClient(create_app(), follow_redirects=False, headers=CSRF)


def test_policy_shows_the_real_thresholds(demo):
    resp = demo.get("/api/policy")
    assert resp.status_code == 200
    assert (
        resp.json()
        == {"medium": MEDIUM_AT, "high": HIGH_AT}
        == {"medium": 30, "high": 60}
    )


@pytest.mark.parametrize("method", ["put", "post", "patch", "delete"])
def test_policy_cannot_be_changed_from_the_web(demo, method):
    # Los umbrales son del codigo (app/decision.py): ningun metodo de escritura existe.
    assert (
        demo.request(method.upper(), "/api/policy", json={"high": 10}).status_code
        == 405
    )
    assert demo.get("/api/policy").json()["high"] == 60


def test_supervisor_can_read_the_policy(demo):
    demo.post("/api/demo/role", json={"role": "supervisor"})
    assert demo.get("/api/policy").status_code == 200


def _text(name):
    return (STATIC / name).read_text(encoding="utf-8")


def test_panel_has_no_threshold_controls_or_auto_quarantine():
    html = _text("index.html")
    js = _text("app.js")
    assert 'type="range"' not in html and "range" not in re.findall(
        r'type="(\w+)"', html
    )
    for banned in (
        "Cuarentena automática",
        "cuarentena automática",
        "autoQuarantine",
        "cfgHighSlider",
    ):
        assert banned not in html and banned not in js
    # no se puede escribir en la politica desde el cliente
    assert not re.search(
        r"api\(\s*[\"']/api/policy[\"']\s*,\s*[\"'](PUT|POST|PATCH)", js
    )


def test_static_files_load_nothing_from_outside():
    for path in (
        list(STATIC.glob("*.html"))
        + list(STATIC.glob("*.css"))
        + list(STATIC.glob("*.js"))
    ):
        text = path.read_text(encoding="utf-8")
        # el espacio de nombres xmlns de un SVG no es una descarga; todo lo demas si lo seria
        text = text.replace("http://www.w3.org/2000/svg", "")
        assert not re.search(r"""(src|href)=["']//""", text), (
            path.name
        )  # enlaces sin protocolo
        assert "http://" not in text and "https://" not in text, path.name
        assert "@import" not in text, path.name


def test_icons_are_local_and_use_no_scripts():
    sprite = _text("icons/sprite.svg")
    assert "<script" not in sprite.lower() and 'href="http' not in sprite
    assert (STATIC / "icons" / "LICENSE-lucide.txt").exists()


def test_no_dangerous_dom_sinks_anywhere_in_the_panel():
    for js in STATIC.glob("*.js"):
        text = js.read_text(encoding="utf-8")
        for sink in (
            ".innerHTML",
            ".outerHTML",
            "insertAdjacentHTML",
            "document.write",
            "eval(",
            "new Function",
        ):
            assert sink not in text, (js.name, sink)


def test_panel_exposes_roles_and_demo_banner_markup():
    html = _text("index.html")
    assert 'id="banner"' in html and "Demostración con datos simulados" in html
    assert 'id="banner-rol"' in html and "solo lectura" in html
    assert 'id="rol-select"' in html and 'id="rol-caja"' in html
    for pane in ("panel", "analitica", "buzones", "historial", "politica"):
        assert f'id="vista-{pane}"' in html


def test_fonts_are_self_hosted_with_swap_and_metric_fallbacks():
    css = _text("style.css")
    for fam in ("inter", "jetbrains-mono"):
        for sub in ("latin", "latin-ext"):
            for w in (400, 500, 600, 700):
                assert (STATIC / "fonts" / f"{fam}-{sub}-{w}-normal.woff2").exists()
    assert css.count("font-display: swap") == 16
    assert "size-adjust" in css and "ascent-override" in css
    assert "googleapis" not in css and "gstatic" not in css
    for page in ("index.html", "login.html", "invite.html", "connected.html"):
        html = _text(page)
        assert re.search(
            r'<link rel="preload" as="font" type="font/woff2" href="/static/fonts/[^"]+" crossorigin>',
            html,
        ), page
        assert "fonts.googleapis" not in html
    notice = _text("fonts/NOTICE.txt")
    assert "SIL OFL" in notice and (STATIC / "fonts" / "LICENSE-inter.txt").exists()
    assert (STATIC / "fonts" / "LICENSE-jetbrains-mono.txt").exists()


def test_panel_has_the_prototype_sections_and_only_real_numbers():
    html = _text("index.html")
    for label in (
        "Panel de Control",
        "Analítica y Tráfico",
        "Usuarios Conectados",
        "Historial de Amenazas",
        "Configuración de Auditoría",
    ):
        assert label in html
    for placeholder in (
        "Buscar empleado o remitente…",
        "Análisis Forense",
        "Cabeceras SMTP",
        "Copiar IoC",
    ):
        assert placeholder in html or placeholder in _text("app.js")
    for invented in (
        "99,4",
        "99.4",
        "412 correos",
        "184 ms",
        "18.492",
        "SOC v3.0",
        "TLP:AMBER",
        "Sentinel",
    ):
        assert invented not in html and invented not in _text("app.js")

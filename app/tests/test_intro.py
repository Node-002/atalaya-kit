"""La intro de inicio sale una sola vez por sesión, nunca con «menos movimiento» y sin botón.

La decisión es JavaScript puro (`app/static/intro.js`): se ejecuta con Node, que el CI de GitHub
trae instalado (si Node no está, esas pruebas se omiten). El resto son comprobaciones de texto.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parents[1] / "static"
INTRO_JS = STATIC / "intro.js"
NODE = shutil.which("node")

RUNNER = """
const fs = require("fs"), vm = require("vm");
const code = fs.readFileSync(process.argv[1], "utf8");
const { reduce, storage, blocked } = JSON.parse(fs.readFileSync(0, "utf8"));
const clases = new Set();
const sessionStorage = {
  getItem: (k) => (k in storage ? storage[k] : null),
  setItem: (k, v) => { if (blocked) throw new Error("bloqueado"); storage[k] = v; },
};
const ctx = {
  window: { matchMedia: () => ({ matches: reduce }) },
  document: { documentElement: { classList: { add: (c) => clases.add(c) } } },
};
ctx.sessionStorage = sessionStorage;
vm.runInNewContext(code, ctx);
process.stdout.write(JSON.stringify({ clases: [...clases], storage }));
"""


def run(reduce=False, storage=None, blocked=False):
    done = subprocess.run(
        [NODE, "-e", RUNNER, str(INTRO_JS)],
        input=json.dumps(
            {"reduce": reduce, "storage": storage or {}, "blocked": blocked}
        ),
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return json.loads(done.stdout)


needs_node = pytest.mark.skipif(NODE is None, reason="Node no esta instalado")


@needs_node
def test_first_visit_of_the_session_shows_the_intro_and_remembers_it():
    out = run()
    assert out["clases"] == ["con-intro"]
    assert out["storage"] == {"atalaya_intro": "1"}


@needs_node
def test_second_visit_in_the_same_session_does_not_show_it():
    out = run(storage={"atalaya_intro": "1"})
    assert out["clases"] == []


@needs_node
def test_reduced_motion_never_shows_it_and_does_not_burn_the_session_flag():
    out = run(reduce=True)
    assert out["clases"] == []
    assert out["storage"] == {}


@needs_node
def test_if_session_storage_is_blocked_the_panel_still_loads_without_the_intro():
    out = run(blocked=True)
    assert out["clases"] == []


def test_the_page_loads_the_intro_script_in_the_head_and_the_overlay_is_decorative_only():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert html.index("/static/intro.js") < html.index("</head>")
    bloque = html[html.index('class="intro"') : html.index('<a class="skip"')]
    assert (
        'aria-hidden="true"'
        in html[html.index('class="intro"') - 20 : html.index('class="intro"') + 40]
    )
    # sin botón de saltar, sin enlaces ni campos dentro de la intro
    for prohibido in ("<button", "<a ", "<input", "tabindex"):
        assert prohibido not in bloque


def test_the_intro_css_only_paints_when_motion_is_allowed_and_removes_itself():
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    base = css[css.index(".intro { display: none; }") :]
    # por defecto está oculta; solo se pinta dentro del bloque «no-preference»
    assert base.index("prefers-reduced-motion: no-preference") < base.index(
        "html.con-intro .intro"
    )
    assert "visibility: hidden" in base  # se quita sola, no deja una capa encima
    assert (
        "pointer-events"
        not in base.split("html.con-intro .intro", 1)[1].split("}", 1)[0]
    )

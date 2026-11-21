"""Las pestañas del panel (Todos, Alta, Media, Baja, Limpios, Cuarentena, Legítimos) reparten los
correos sin repetirlos, y la última decisión de una persona es la que manda.

Las reglas son JavaScript puro (`app/static/estado.js`): se ejecutan con Node, que el CI de
GitHub trae instalado. Si Node no está, la prueba se omite.
"""

import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

ESTADO_JS = Path(__file__).resolve().parents[1] / "static" / "estado.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node no esta instalado")

RUNNER = """
const fs = require("fs"), vm = require("vm");
const code = fs.readFileSync(process.argv[1], "utf8");
const casos = JSON.parse(fs.readFileSync(0, "utf8"));
const api = vm.runInNewContext(code + "\\n;({ FILTERS, lastHuman, finalState, riskKey })", {});
const out = casos.map((a) => ({
  tabs: api.FILTERS.filter((f) => f.match(a)).map((f) => f.key),
  final: api.finalState(a),
  last: api.lastHuman(a),
}));
process.stdout.write(JSON.stringify(out));
"""

REPARTO = ["high", "medium", "low", "safe", "quarantine", "legit"]  # todas menos «all»


def run(alerts):
    done = subprocess.run(
        [NODE, "-e", RUNNER, str(ESTADO_JS)],
        input=json.dumps(alerts),
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return json.loads(done.stdout)


def alerta(risk="high", status="pending_approval", acciones=(), signals=1):
    return {
        "risk": risk,
        "status": status,
        "signals": [{"code": "x"}] * signals,
        "actions": [{"type": t} for t in acciones],
    }


def tabs(a):
    return run([a])[0]["tabs"]


def test_a_pending_high_alert_is_only_in_all_and_high():
    assert tabs(alerta()) == ["all", "high"]


def test_quarantining_moves_the_alert_out_of_its_risk_tab():
    # el caso que se veia duplicado: seguia contando en Alta y en Cuarentena
    assert tabs(alerta(status="quarantined", acciones=["quarantine"])) == [
        "all",
        "quarantine",
    ]
    assert tabs(alerta("medium", "quarantined", ["quarantine"])) == [
        "all",
        "quarantine",
    ]
    assert tabs(alerta("low", "quarantined", ["quarantine"], signals=0)) == [
        "all",
        "quarantine",
    ]


def test_marking_legit_moves_it_to_legitimos_only():
    a = alerta("high", "dismissed", ["mark_legit"])
    assert tabs(a) == ["all", "legit"]


def test_the_last_human_decision_wins_when_it_goes_back_to_quarantine():
    # legitimo -> cuarentena: ya NO debe seguir en Legitimos (ni antes ni despues de recargar)
    a = alerta("high", "quarantined", ["quarantine", "mark_legit", "quarantine"])
    assert tabs(a) == ["all", "quarantine"]
    # y si solo consta «legitimo» y luego cuarentena
    assert tabs(alerta("high", "quarantined", ["mark_legit", "quarantine"])) == [
        "all",
        "quarantine",
    ]


def test_quarantine_then_release_then_quarantine_again_follows_the_current_state():
    pasos = [
        (alerta("high", "quarantined", ["quarantine"]), ["all", "quarantine"]),
        (alerta("high", "dismissed", ["quarantine", "mark_legit"]), ["all", "legit"]),
        (
            alerta("high", "quarantined", ["quarantine", "mark_legit", "quarantine"]),
            ["all", "quarantine"],
        ),
    ]
    for a, esperado in pasos:
        assert tabs(a) == esperado


def test_keeping_it_in_the_inbox_leaves_it_in_its_risk_tab():
    assert tabs(alerta("high", "labeled", ["reject_quarantine"])) == ["all", "high"]


def test_clean_emails_have_their_own_tab_and_low_risk_with_signals_stay_in_low():
    assert tabs(alerta("low", "dismissed", signals=0)) == ["all", "safe"]
    assert tabs(alerta("low", "labeled", signals=1)) == ["all", "low"]


def test_a_clean_email_marked_legit_or_quarantined_leaves_limpios():
    assert tabs(alerta("low", "quarantined", ["quarantine"], signals=0)) == [
        "all",
        "quarantine",
    ]
    assert tabs(alerta("low", "dismissed", ["mark_legit"], signals=0)) == [
        "all",
        "legit",
    ]


def test_the_tabs_partition_every_possible_alert_without_repeats():
    """Cualquier combinacion de riesgo, estado, senales y decisiones cae en UNA sola pestana."""
    rng = random.Random(21)
    tipos = ["quarantine", "reject_quarantine", "mark_legit"]
    casos = []
    for _ in range(400):
        estado = rng.choice(
            ["new", "labeled", "pending_approval", "quarantined", "dismissed"]
        )
        casos.append(
            alerta(
                rng.choice(["high", "medium", "low"]),
                estado,
                [rng.choice(tipos) for _ in range(rng.randint(0, 4))],
                signals=rng.randint(0, 3),
            )
        )
    for resultado in run(casos):
        reparto = [t for t in resultado["tabs"] if t in REPARTO]
        assert len(reparto) == 1, resultado
        assert resultado["tabs"][0] == "all"


def test_the_page_loads_the_rules_before_the_panel_script():
    html = (ESTADO_JS.parent / "index.html").read_text(encoding="utf-8")
    assert html.index("/static/estado.js") < html.index("/static/app.js")
    # y app.js ya no define sus propias reglas (para que no se desincronicen)
    js = (ESTADO_JS.parent / "app.js").read_text(encoding="utf-8")
    assert "const FILTERS" not in js and "const lastHuman" not in js

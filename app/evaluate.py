"""Mide aciertos y falsos positivos de las reglas sobre el corpus de prueba.

Uso:  python -m app.evaluate            (tabla y metricas)
      python -m app.evaluate --json     (salida para el pitch)

Un correo cuenta como "marcado" si el riesgo es medio o alto.
El corpus es sintetico y lo escribio el desarrollador: las cifras son orientativas.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from app import analyzers, decision
from app.models import Message, Risk

CORPUS = Path(__file__).parent / "tests" / "fixtures" / "corpus.json"


def load_cases(path: Path = CORPUS) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def to_message(case: dict) -> Message:
    return Message(
        ref=case["id"],
        received_at=datetime(2026, 11, 20, tzinfo=UTC),
        sender=case["sender"],
        reply_to=case.get("reply_to"),
        subject=case["subject"],
        body=case["body"],
        headers={"Authentication-Results": case["auth"]},
        links=case.get("links", []),
    )


def evaluate(cases: list[dict]) -> dict:
    rows = []
    for case in cases:
        signals = analyzers.analyze(to_message(case))
        risk = decision.risk_of(signals)
        rows.append(
            {
                "id": case["id"],
                "label": case["label"],
                "note": case["note"],
                "risk": risk.value,
                "score": decision.score(signals),
                "signals": [s.code for s in signals],
                "flagged": risk is not Risk.low,
            }
        )
    phish = [r for r in rows if r["label"] == "phish"]
    legit = [r for r in rows if r["label"] == "legit"]
    detected = [r for r in phish if r["flagged"]]
    false_pos = [r for r in legit if r["flagged"]]
    high = [r for r in rows if r["risk"] == "high"]
    high_ok = [r for r in high if r["label"] == "phish"]
    return {
        "total": len(rows),
        "phish": len(phish),
        "legit": len(legit),
        "detected": len(detected),
        "missed": [r["id"] for r in phish if not r["flagged"]],
        "false_positives": [r["id"] for r in false_pos],
        "detection_rate": len(detected) / len(phish),
        "false_positive_rate": len(false_pos) / len(legit),
        "high_flagged": len(high),
        "high_precision": (len(high_ok) / len(high)) if high else None,
        "rows": rows,
    }


def main() -> None:
    result = evaluate(load_cases())
    if "--json" in sys.argv:
        print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
        return
    print(f"{'ID':<5}{'real':<7}{'riesgo':<8}{'pts':>4}  senales")
    for r in result["rows"]:
        ok = (r["label"] == "phish") == r["flagged"]
        mark = " " if ok else "  <-- FALLO"
        print(
            f"{r['id']:<5}{r['label']:<7}{r['risk']:<8}{r['score']:>4}  {','.join(r['signals']) or '-'}{mark}"
        )
    d, p = result["detected"], result["phish"]
    fp, lg = len(result["false_positives"]), result["legit"]
    print()
    print(
        f"Phishing detectado (medio o alto): {d}/{p} = {result['detection_rate']:.0%}  | no detectados: {result['missed']}"
    )
    print(
        f"Falsos positivos:                  {fp}/{lg} = {result['false_positive_rate']:.0%}  | {result['false_positives']}"
    )
    if result["high_precision"] is not None:
        print(
            f"Precision de 'riesgo alto':        {result['high_precision']:.0%} de {result['high_flagged']} marcados"
        )


if __name__ == "__main__":
    main()

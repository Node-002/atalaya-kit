"""Informes en PDF con plantilla, para quien supervisa (no solo para quien programa).

Dos documentos: el informe de un correo y el informe de la organizacion. Tienen la misma plantilla:
encabezado con la marca, resumen, tablas, notas para leerlo y un bloque de firma.

Seguridad: todo texto que venga de un correo o de una persona pasa por `_safe`, que
1) escapa el marcado que entiende ReportLab (un asunto como `<b>` o `&nbsp;` no puede romper ni
   inyectar nada en el documento), y
2) sustituye lo que la fuente del PDF no puede dibujar por `[U+XXXX]`. Asi un dominio con una letra
   cirilica ("bаncogeneral") se ve como `b[U+0430]ncogeneral`: en un informe de seguridad eso es
   justo lo que hay que ver, en lugar de un cuadro negro o de una letra identica a la latina.
No incluye nunca el contenido de los correos ni sus adjuntos (Atalaya no los guarda).
"""

from __future__ import annotations

import html
from collections import Counter
from datetime import UTC, datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.campaigns import Campaign
from app.decision import HIGH_AT, MEDIUM_AT
from app.models import HUMAN_ACTIONS, Alert, Status
from app.report import (
    AUDIT_TEXT,
    DECISION_TEXT,
    RISK_TEXT,
    SOURCE_TEXT,
    _final_state,
)

ACCENT = colors.HexColor("#1f6feb")
INK = colors.HexColor("#1f2933")
MUTED = colors.HexColor("#5b6770")
LINE = colors.HexColor("#c9d1d9")
SHADE = colors.HexColor("#eef2f7")
RISK_COLOR = {
    "high": colors.HexColor("#b42318"),
    "medium": colors.HexColor("#b54708"),
    "low": colors.HexColor("#067647"),
}

# Tope de filas por tabla: con 200 buzones el informe sigue siendo legible y de tamano razonable.
MAX_MAILBOXES = 60
MAX_DECISIONS = 100
MAX_AUDIT = 50

_PUNCT = {
    "‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
    "—": "-", "…": "...", "•": "*", " ": " ",
}  # fmt: skip


def _safe(text: object) -> str:
    """Texto no confiable -> texto seguro para un Paragraph (ver el docstring del modulo)."""
    out: list[str] = []
    for ch in str(text):
        ch = _PUNCT.get(ch, ch)
        code = ord(ch)
        if ch in "\r\n\t":
            out.append(" ")
        elif code < 32 or 0x7F <= code < 0xA0:
            continue
        elif code <= 0xFF:
            out.append(ch)
        elif len(ch) == 1:
            out.append(f"[U+{code:04X}]")
        else:  # multiples caracteres (de _PUNCT)
            out.append(ch)
    return html.escape("".join(out), quote=False)


def _when(at: datetime) -> str:
    return at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


# --- Estilos ---------------------------------------------------------------------------------
def _style(name: str, **kw) -> ParagraphStyle:
    base = dict(fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK, spaceAfter=4)
    base.update(kw)
    return ParagraphStyle(name, **base)


BODY = _style("body")
SMALL = _style("small", fontSize=8, leading=10.5, textColor=MUTED)
TITLE = _style("title", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=ACCENT, spaceAfter=2)
SUBTITLE = _style("subtitle", fontSize=11.5, leading=15, textColor=MUTED, spaceAfter=10)
H2 = _style("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=ACCENT, spaceBefore=14, spaceAfter=5)
CELL = _style("cell", fontSize=8.4, leading=10.6, spaceAfter=0)
CELLB = _style("cellb", fontName="Helvetica-Bold", fontSize=8.4, leading=10.6, spaceAfter=0)
CELLH = _style("cellh", fontName="Helvetica-Bold", fontSize=8.4, leading=10.6, textColor=colors.white, spaceAfter=0)
KPI_N = _style("kpin", fontName="Helvetica-Bold", fontSize=20, leading=23, spaceAfter=0, alignment=1)
KPI_L = _style("kpil", fontSize=7.8, leading=9.6, textColor=MUTED, spaceAfter=0, alignment=1)


def p(text: object, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(_safe(text), style)


def pm(markup: str, style: ParagraphStyle = BODY) -> Paragraph:
    """Para textos propios de la plantilla que llevan negritas (nunca texto de un correo)."""
    return Paragraph(markup, style)


# --- Marca, encabezado y pie ----------------------------------------------------------------
def _draw_shield(c: rl_canvas.Canvas, x: float, y: float, size: float) -> None:
    """El escudo de Atalaya dibujado con vectores (no depende de archivos de imagen)."""
    s = size / 64.0
    c.saveState()
    c.translate(x, y)
    c.scale(s, s)
    path = c.beginPath()
    path.moveTo(32, 62)
    path.lineTo(10, 52)
    path.lineTo(10, 32)
    path.curveTo(10, 16, 20, 7, 32, 2)
    path.curveTo(44, 7, 54, 16, 54, 32)
    path.lineTo(54, 52)
    path.close()
    c.setFillColor(colors.HexColor("#12202f"))
    c.setStrokeColor(ACCENT)
    c.setLineWidth(3)
    c.drawPath(path, fill=1, stroke=1)
    c.setLineWidth(3)
    c.circle(32, 32, 8, stroke=1, fill=0)
    c.setFillColor(ACCENT)
    c.circle(32, 32, 3, stroke=0, fill=1)
    c.restoreState()


class _NumberedCanvas(rl_canvas.Canvas):
    """Pone "Pagina x de y" en cada hoja (hace falta conocer el total antes de dibujar)."""

    doc_title = ""
    generated = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved: list[dict] = []

    def showPage(self):  # noqa: N802 (nombre de ReportLab)
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            self._decorate(total)
            super().showPage()
        super().save()

    def _decorate(self, total: int) -> None:
        w, h = letter
        self.saveState()
        _draw_shield(self, 0.75 * inch, h - 0.78 * inch, 22)
        self.setFillColor(ACCENT)
        self.setFont("Helvetica-Bold", 13)
        self.drawString(0.75 * inch + 29, h - 0.68 * inch, "Atalaya")
        self.setFillColor(MUTED)
        self.setFont("Helvetica", 8.5)
        self.drawRightString(w - 0.75 * inch, h - 0.66 * inch, self.doc_title)
        self.setStrokeColor(LINE)
        self.setLineWidth(0.6)
        self.line(0.75 * inch, h - 0.88 * inch, w - 0.75 * inch, h - 0.88 * inch)
        self.line(0.75 * inch, 0.78 * inch, w - 0.75 * inch, 0.78 * inch)
        self.setFont("Helvetica", 7.6)
        self.drawString(0.75 * inch, 0.6 * inch, "Confidencial. No incluye el contenido de los correos ni sus adjuntos.")
        self.drawString(0.75 * inch, 0.46 * inch, f"Generado el {self.generated}")
        self.drawRightString(w - 0.75 * inch, 0.6 * inch, f"Página {self._pageNumber} de {total}")
        self.restoreState()


def _doc(buffer: BytesIO, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=1.1 * inch,
        bottomMargin=0.95 * inch,
        title=title,
        author="Atalaya",
        subject="Informe de revisión de correo",
    )


def _build(story: list, title: str, generated: str) -> bytes:
    buffer = BytesIO()

    class Canvas(_NumberedCanvas):
        doc_title = title
        # el valor se fija al construir; es solo texto fijo del informe

    Canvas.generated = generated
    _doc(buffer, title).build(story, canvasmaker=Canvas)
    return buffer.getvalue()


# --- Piezas reutilizables -------------------------------------------------------------------
def _table(rows: list[list[Paragraph]], widths: list[float], header: bool = True) -> Table:
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SHADE]),
        ]
    t.setStyle(TableStyle(style))
    return t


def _kpis(items: list[tuple[str, int, colors.Color | None]]) -> Table:
    cells = [
        [
            Paragraph(
                f'<font color="{(color or INK).hexval().replace("0x", "#")}">{n}</font>', KPI_N
            ),
            Paragraph(_safe(label), KPI_L),
        ]
        for label, n, color in items
    ]
    cols = [list(c) for c in zip(*cells, strict=True)]
    w = (letter[0] - 1.5 * inch) / len(items)
    t = Table(cols, colWidths=[w] * len(items))
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("BACKGROUND", (0, 0), (-1, -1), SHADE),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return t


def _signature_block() -> KeepTogether:
    w = letter[0] - 1.5 * inch
    line = _style("sig", fontSize=8.5, textColor=MUTED, spaceAfter=0)
    rows = [
        [Paragraph("Revisado por", line), Paragraph("Cargo", line)],
        [Paragraph("&nbsp;", BODY), Paragraph("&nbsp;", BODY)],
        [Paragraph("Fecha", line), Paragraph("Firma", line)],
        [Paragraph("&nbsp;", BODY), Paragraph("&nbsp;", BODY)],
    ]
    t = Table(rows, colWidths=[w / 2 - 8, w / 2 - 8], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 1), (-1, 1), 0.6, INK),
                ("LINEBELOW", (0, 3), (-1, 3), 0.6, INK),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
                ("BOTTOMPADDING", (0, 3), (-1, 3), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    return KeepTogether([p("Conformidad", H2), t])


def _how_to_read() -> list:
    return [
        p("Cómo leer este informe", H2),
        pm(
            f"<b>Riesgo.</b> Es una suma de puntos de señales calculadas por código: <b>alto</b> desde {HIGH_AT} "
            f"puntos, <b>medio</b> desde {MEDIUM_AT}, <b>bajo</b> por debajo. La IA solo redacta la explicación; "
            "no decide ni cambia el riesgo."
        ),
        pm(
            "<b>Decisión.</b> Atalaya nunca borra ni envía correos. La <b>cuarentena</b> saca el mensaje de la "
            "bandeja y le pone una etiqueta, solo con la aprobación de una persona, y se puede revertir."
        ),
        pm(
            "<b>Privacidad.</b> Este documento no contiene el texto de los correos ni sus adjuntos: Atalaya solo "
            "guarda el veredicto, las señales, un identificador y el estado."
        ),
    ]


def _risk_chip(risk_value: str) -> Paragraph:
    color = RISK_COLOR[risk_value].hexval().replace("0x", "#")
    return Paragraph(f'<font color="{color}"><b>{_safe(RISK_TEXT[risk_value].upper())}</b></font>', CELL)


def _decisions(alert: Alert) -> list:
    return [a for a in alert.actions if a.type in HUMAN_ACTIONS]


def _reason(action) -> str:
    return " ".join(action.reason.split()) if action.reason else "(sin motivo escrito: aceptó el análisis de Atalaya)"


# --- Informe de un correo -------------------------------------------------------------------
def build_alert_pdf(alert: Alert, org_name: str) -> bytes:
    now = datetime.now(UTC)
    score = sum(s.weight for s in alert.signals)
    w = letter[0] - 1.5 * inch
    story: list = [
        p("Informe de revisión de un correo", TITLE),
        p(org_name, SUBTITLE),
    ]
    meta = [
        ("Identificador de la alerta", alert.id),
        ("Buzón", alert.mailbox_label or "(sin nombre)"),
        ("Dominio del remitente", alert.sender_domain),
        ("Recibido", _when(alert.received_at)),
        ("Estado actual", _final_state(alert)),
    ]
    story.append(
        _table([[p(k, CELLB), p(v, CELL)] for k, v in meta], [w * 0.3, w * 0.7], header=False)
    )

    story.append(p("1. Qué detectó Atalaya (automático)", H2))
    story.append(
        _table(
            [
                [p("Riesgo", CELLH), p("Puntos", CELLH), p("Origen del resumen", CELLH)],
                [
                    _risk_chip(alert.risk.value),
                    p(score, CELL),
                    p(SOURCE_TEXT.get(alert.explanation_source, alert.explanation_source), CELL),
                ],
            ],
            [w * 0.25, w * 0.2, w * 0.55],
        )
    )
    story.append(Spacer(1, 6))
    story.append(p(" ".join(alert.explanation.split()), BODY))
    if alert.signals:
        rows = [[p("Señal detectada", CELLH), p("Puntos", CELLH)]]
        rows += [[p(s.description, CELL), p(s.weight, CELL)] for s in alert.signals]
        story.append(_table(rows, [w * 0.86, w * 0.14]))
    else:
        story.append(p("No se detectó ninguna señal de riesgo.", BODY))

    story.append(p("2. Decisiones de las personas", H2))
    human = _decisions(alert)
    if not human:
        story.append(p("Todavía no hay decisiones humanas sobre este correo.", BODY))
    else:
        rows = [[p("Fecha", CELLH), p("Persona", CELLH), p("Decisión", CELLH), p("Motivo", CELLH)]]
        for a in human:
            rows.append(
                [p(_when(a.at), CELL), p(a.by, CELL), p(DECISION_TEXT.get(a.type, a.type), CELL), p(_reason(a), CELL)]
            )
        story.append(_table(rows, [w * 0.19, w * 0.17, w * 0.28, w * 0.36]))

    story.append(p("3. Resultado", H2))
    story.append(pm(f"<b>Estado final:</b> {_safe(_final_state(alert))}."))
    story += _how_to_read()
    story.append(_signature_block())
    return _build(story, "Informe de revisión de un correo", _when(now))


# --- Informe de la organizacion -------------------------------------------------------------
def build_org_pdf(
    org_name: str,
    alerts: list[Alert],
    audit: list[dict],
    campaigns: list[Campaign],
    generated_by: str = "",
) -> bytes:
    now = datetime.now(UTC)
    w = letter[0] - 1.5 * inch
    risks = Counter(a.risk.value for a in alerts)
    quarantined = sum(a.status is Status.quarantined for a in alerts)
    pending = sum(a.status is Status.pending_approval for a in alerts)
    reviewed = sum(bool(_decisions(a)) for a in alerts)
    boxes = {a.mailbox_id: a.mailbox_label or a.mailbox_id for a in alerts}

    story: list = [p("Informe de la organización", TITLE), p(org_name, SUBTITLE)]
    if generated_by:
        story.append(p(f"Generado por: {generated_by}", SMALL))
    story.append(Spacer(1, 4))

    story.append(p("1. Resumen", H2))
    story.append(
        _kpis(
            [
                ("Correos analizados", len(alerts), None),
                ("Riesgo alto", risks["high"], RISK_COLOR["high"]),
                ("Riesgo medio", risks["medium"], RISK_COLOR["medium"]),
                ("Riesgo bajo", risks["low"], RISK_COLOR["low"]),
            ]
        )
    )
    story.append(Spacer(1, 5))
    story.append(
        _kpis(
            [
                ("Esperan una decisión", pending, RISK_COLOR["high"] if pending else None),
                ("En cuarentena", quarantined, None),
                ("Revisados por una persona", reviewed, None),
                ("Campañas detectadas", len(campaigns), None),
            ]
        )
    )

    story.append(p("2. Estado por buzón", H2))
    if not boxes:
        story.append(p("Todavía no hay correos analizados.", BODY))
    else:
        per: dict[str, Counter] = {b: Counter() for b in boxes}
        for a in alerts:
            c = per[a.mailbox_id]
            c["total"] += 1
            c[a.risk.value] += 1
            c["quarantined"] += a.status is Status.quarantined
            c["pending"] += a.status is Status.pending_approval
        ordered = sorted(boxes, key=lambda b: (-per[b]["pending"], -per[b]["high"], boxes[b]))
        rows = [
            [p(h, CELLH) for h in ("Buzón", "Correos", "Alto", "Medio", "En cuarentena", "Esperan decisión")]
        ]
        for b in ordered[:MAX_MAILBOXES]:
            c = per[b]
            rows.append(
                [p(boxes[b], CELL)]
                + [p(c[k], CELL) for k in ("total", "high", "medium", "quarantined", "pending")]
            )
        story.append(_table(rows, [w * 0.34, w * 0.1, w * 0.1, w * 0.1, w * 0.18, w * 0.18]))
        if len(ordered) > MAX_MAILBOXES:
            story.append(
                p(f"Se muestran los {MAX_MAILBOXES} buzones con más urgencia de {len(ordered)}.", SMALL)
            )

    story.append(p("3. Campañas detectadas", H2))
    if not campaigns:
        story.append(p("No se detectó el mismo ataque en más de un buzón.", BODY))
    else:
        story.append(
            p(
                "Una campaña es el mismo ataque llegando a varios buzones. Se puede aislar de una sola vez, "
                "con la misma regla de motivo y una anotación por cada correo.",
                SMALL,
            )
        )
        rows = [[p(h, CELLH) for h in ("Dominio del remitente", "Riesgo", "Buzones", "Aislados")]]
        for c in campaigns:
            isolated = len(c.alert_ids) - c.actionable
            rows.append(
                [
                    p(c.sender_domain, CELL),
                    _risk_chip(c.risk.value),
                    p(c.mailbox_count, CELL),
                    p(f"{isolated} de {len(c.alert_ids)}", CELL),
                ]
            )
        story.append(_table(rows, [w * 0.46, w * 0.16, w * 0.14, w * 0.24]))

    story.append(p("4. Decisiones de las personas (más recientes primero)", H2))
    decisions = sorted(
        ((x.at, x.by, a, x) for a in alerts for x in a.actions if x.type in HUMAN_ACTIONS),
        key=lambda r: r[0],
        reverse=True,
    )
    if not decisions:
        story.append(p("Todavía no hay decisiones humanas.", BODY))
    else:
        rows = [[p(h, CELLH) for h in ("Fecha", "Persona", "Buzón / dominio", "Decisión", "Motivo")]]
        for at, by, a, x in decisions[:MAX_DECISIONS]:
            rows.append(
                [
                    p(_when(at), CELL),
                    p(by, CELL),
                    p(f"{a.mailbox_label or 'buzón'} / {a.sender_domain}", CELL),
                    p(DECISION_TEXT.get(x.type, x.type), CELL),
                    p(_reason(x), CELL),
                ]
            )
        story.append(_table(rows, [w * 0.15, w * 0.13, w * 0.24, w * 0.22, w * 0.26]))
        if len(decisions) > MAX_DECISIONS:
            story.append(p(f"Se muestran las {MAX_DECISIONS} más recientes de {len(decisions)}.", SMALL))

    story.append(p("5. Actividad registrada", H2))
    if not audit:
        story.append(p("Sin actividad registrada.", BODY))
    else:
        rows = [[p(h, CELLH) for h in ("Fecha", "Quién", "Qué pasó")]]
        for e in audit[:MAX_AUDIT]:
            text = AUDIT_TEXT.get(e["action"], e["action"])
            detail = " ".join(str(e.get("detail") or "").split())
            if detail:
                text += f" ({detail[:90]})"
            rows.append([p(str(e["at"])[:19].replace("T", " "), CELL), p(e["actor"], CELL), p(text, CELL)])
        story.append(_table(rows, [w * 0.2, w * 0.22, w * 0.58]))

    story += _how_to_read()
    story.append(_signature_block())
    return _build(story, "Informe de la organización", _when(now))


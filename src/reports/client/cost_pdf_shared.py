"""Constantes y helpers compartidos para el PDF de costos."""

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

INK    = colors.HexColor("#0f172a")
MUTED  = colors.HexColor("#64748b")
BORDER = colors.HexColor("#e2e8f0")
BG_ALT = colors.HexColor("#f8fafc")
WHITE  = colors.white
DARK   = colors.HexColor("#1e293b")
GREEN  = colors.HexColor("#15803d")
BLUE   = colors.HexColor("#1d4ed8")
INDIGO = colors.HexColor("#4f46e5")
VIOLET = colors.HexColor("#6d28d9")


def _fmt_usd(v) -> str:
    v = float(v or 0)
    if v >= 1000:
        return f"USD ${v/1000:.1f}K"
    return f"USD ${v:.2f}"


def _pct(v) -> str:
    return f"{float(v or 0):.1f}%"


def _kpi(label, value, sub, bg_hex, fg_hex, w):
    tbl = Table([
        [Paragraph(label, ParagraphStyle("kpi_lbl", fontSize=8, textColor=MUTED))],
        [Paragraph(value, ParagraphStyle("kpi_val", fontSize=16, fontName="Helvetica-Bold", textColor=fg_hex))],
        [Paragraph(sub, ParagraphStyle("kpi_sub", fontSize=7, textColor=MUTED))],
    ], colWidths=[w])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor(bg_hex)),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX",           (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    return tbl


def _section(title, styles):
    return [
        Spacer(1, 14),
        Paragraph(title, ParagraphStyle("h2", fontSize=12, fontName="Helvetica-Bold", textColor=INK)),
        Spacer(1, 6),
    ]


def _bar_cell(pct: float, bar_total_w: float, bar_color, bg_color) -> Table:
    pct = float(pct or 0)
    pct = max(0.0, min(pct, 100.0))
    bar_w = max(1, int((pct / 100) * bar_total_w))
    data = [[
        Paragraph(_pct(pct), ParagraphStyle("pct", fontSize=7, textColor=INK)),
        "",
    ]]
    tbl = Table(data, colWidths=[28, bar_total_w])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), None),
        ("BACKGROUND", (1, 0), (1, 0), bg_color),
        ("INNERGRID",  (1, 0), (1, 0), 0, bg_color),
    ]))
    # draw bar as another table overlay
    bar = Table([[" "]], colWidths=[bar_w], rowHeights=[8])
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bar_color),
    ]))
    tbl._cellvalues[0][1] = bar
    return tbl


def _kpi_row(cards, col_w, usable_w):
    cells = [_kpi(*c, col_w, c[4]) if len(c) == 5 else _kpi(*c, col_w) for c in cards]
    row = Table([cells], colWidths=[usable_w / len(cells)] * len(cells))
    row.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return row

"""Estilos, paletas y helpers visuales del reporte de Riesgo & Compliance."""

from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, HRFlowable, Spacer
from reportlab.lib import colors

# ── Paleta ────────────────────────────────────────────────────────────────────
INK    = colors.HexColor("#0f172a")
MUTED  = colors.HexColor("#64748b")
BORDER = colors.HexColor("#e2e8f0")
BG_ALT = colors.HexColor("#f8fafc")
WHITE  = colors.white
DARK   = colors.HexColor("#1e293b")
RED    = colors.HexColor("#dc2626")
AMBER  = colors.HexColor("#d97706")
GREEN  = colors.HexColor("#16a34a")

RISK_FG = {
    "LOW":      "#16a34a",
    "MEDIUM":   "#d97706",
    "HIGH":     "#dc2626",
    "CRITICAL": "#9f1239",
}
RISK_BG = {
    "LOW":      "#f0fdf4",
    "MEDIUM":   "#fffbeb",
    "HIGH":     "#fef2f2",
    "CRITICAL": "#fff1f2",
}


# ── Formatters ────────────────────────────────────────────────────────────────
def fmt_usd(v) -> str:
    v = float(v or 0)
    return f"USD ${v/1000:.1f}K" if v >= 1000 else f"USD ${v:.2f}"


def fmt_pct(v) -> str:
    return f"{float(v or 0):.1f}%"


# ── Widget helpers ────────────────────────────────────────────────────────────
def kpi_cell(label, value, sub, bg_hex, fg_hex, w):
    bg = colors.HexColor(bg_hex)
    fg = colors.HexColor(fg_hex)
    t = Table(
        [
            [Paragraph(label, ParagraphStyle("kl", fontSize=7.5, textColor=MUTED, leading=10))],
            [Paragraph(value, ParagraphStyle("kv", fontSize=14, textColor=fg, leading=17, fontName="Helvetica-Bold"))],
            [Paragraph(sub,   ParagraphStyle("ks", fontSize=7,   textColor=MUTED, leading=9))],
        ],
        colWidths=[w - 14],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def bar_cell(pct: float, bar_total_w: float, bar_color, bg_color) -> Table:
    filled = max(2.0, pct / 100 * bar_total_w)
    empty  = max(0.0, bar_total_w - filled)
    if empty < 1:
        data, cw = [[""]], [bar_total_w]
    else:
        data, cw = [["", ""]], [filled, empty]
    t = Table(data, colWidths=cw, rowHeights=[8])
    cmds = [
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("BACKGROUND",    (0, 0), (0, -1),  bar_color),
    ]
    if empty >= 1:
        cmds.append(("BACKGROUND", (1, 0), (1, -1), bg_color))
    t.setStyle(TableStyle(cmds))
    return t


def section_header(title, styles):
    return [
        Spacer(1, 10),
        Paragraph(title, styles["sec"]),
        HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6),
    ]


def kpi_row(cards, usable_w):
    n = len(cards)
    w = (usable_w - 4 * (n - 1)) / n
    cells = [kpi_cell(*c, w=w) for c in cards]
    t = Table([cells], colWidths=[w + 4] * n)
    t.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def build_styles(styles):
    """Add custom paragraph styles to the stylesheet."""
    styles.add(ParagraphStyle("sec", fontSize=10, fontName="Helvetica-Bold",
                              textColor=DARK, spaceBefore=4, spaceAfter=2))
    styles.add(ParagraphStyle("th", fontSize=8, fontName="Helvetica-Bold",
                              textColor=WHITE, leading=10))
    styles.add(ParagraphStyle("td", fontSize=8, textColor=INK, leading=10))
    styles.add(ParagraphStyle("tds", fontSize=7, textColor=MUTED, leading=9))
    return styles

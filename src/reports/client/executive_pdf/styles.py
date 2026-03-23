"""
EXECUTIVE PDF — STYLES
======================
Color palette, paragraph styles, KPI card builder,
section header helper, and percentage-bar helper.
"""

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# =====================================================
#   PALETTE
# =====================================================
INK    = colors.HexColor("#0f172a")
MUTED  = colors.HexColor("#64748b")
BORDER = colors.HexColor("#e2e8f0")
BG_ALT = colors.HexColor("#f8fafc")
WHITE  = colors.white
DARK   = colors.HexColor("#1e293b")
ACCENT = colors.HexColor("#2563eb")
GREEN  = colors.HexColor("#16a34a")
RED    = colors.HexColor("#dc2626")
AMBER  = colors.HexColor("#d97706")
INDIGO = colors.HexColor("#4f46e5")

RISK_COLOR = {
    "LOW":      colors.HexColor("#16a34a"),
    "MEDIUM":   colors.HexColor("#d97706"),
    "HIGH":     colors.HexColor("#dc2626"),
    "CRITICAL": colors.HexColor("#9f1239"),
}


# =====================================================
#   FORMATTERS
# =====================================================
def _fmt_usd(value) -> str:
    v = float(value or 0)
    if v >= 1000:
        return f"USD ${v/1000:.1f}K"
    return f"USD ${v:.2f}"


def _pct(value) -> str:
    return f"{float(value or 0):.1f}%"


# =====================================================
#   PARAGRAPH STYLES
# =====================================================
def build_styles():
    """Return the extended ReportLab stylesheet used throughout the report."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "section",
        fontSize=10, fontName="Helvetica-Bold",
        textColor=DARK, spaceBefore=4, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "th", fontSize=8, fontName="Helvetica-Bold",
        textColor=WHITE, leading=10,
    ))
    styles.add(ParagraphStyle(
        "td", fontSize=8, textColor=INK, leading=10,
    ))
    styles.add(ParagraphStyle(
        "tds", fontSize=7, textColor=MUTED, leading=9,
    ))
    return styles


# =====================================================
#   KPI CARD  (table cell simulating a card)
# =====================================================
def _kpi_card(label: str, value: str, sub: str, bg_hex: str, fg_hex: str, w: float):
    bg = colors.HexColor(bg_hex)
    fg = colors.HexColor(fg_hex)
    inner = Table(
        [
            [Paragraph(label, ParagraphStyle("kl", fontSize=7.5, textColor=MUTED, leading=10))],
            [Paragraph(value, ParagraphStyle("kv", fontSize=15, textColor=fg, leading=18, fontName="Helvetica-Bold"))],
            [Paragraph(sub,   ParagraphStyle("ks", fontSize=7,   textColor=MUTED, leading=9))],
        ],
        colWidths=[w - 16],
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return inner


# =====================================================
#   SECTION HEADER
# =====================================================
def _section(title: str, styles) -> list:
    return [
        Spacer(1, 10),
        Paragraph(title, styles["section"]),
        HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6),
    ]


# =====================================================
#   PERCENTAGE BAR
# =====================================================
def _pct_bar(pct: float, bar_color, bar_w: float = 180) -> Table:
    """Barra visual proporcional al porcentaje usando celdas con fondo de color."""
    filled = max(2.0, pct / 100 * bar_w)
    empty  = max(0.1, bar_w - filled)
    inner  = Table([[Spacer(filled, 7), Spacer(empty, 7)]],
                   colWidths=[filled, empty])
    inner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), bar_color),
        ("BACKGROUND",    (1, 0), (1, 0), colors.HexColor("#e2e8f0")),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    return inner

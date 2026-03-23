"""Secciones de findings para el PDF ejecutivo."""

from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

from .styles import (
    INK, MUTED, BORDER, BG_ALT, WHITE, DARK, ACCENT,
    GREEN, RED, AMBER, _kpi_card, _section, _pct_bar, _fmt_usd, _pct,
)


def build_findings_cards(styles, usable_w: float, stats_raw: dict) -> list:
    total_f    = int(stats_raw.get("total", 0))
    active_f   = int(stats_raw.get("active", 0))
    resolved_f = int(stats_raw.get("resolved", 0))
    high_f     = int(stats_raw.get("high", 0))

    finding_card_w = (usable_w - 12) / 4
    finding_cards = [
        ("Total Findings",  str(total_f),    "Detectados",               "#f8fafc", "#334155"),
        ("Activos",         str(active_f),   "Requieren acción",         "#fef2f2", "#dc2626"),
        ("Resueltos",       str(resolved_f), "Optimizaciones aplicadas", "#f0fdf4", "#16a34a"),
        ("Alta Severidad",  str(high_f),     "Prioridad inmediata",      "#fff7ed", "#ea580c"),
    ]
    fc_cells = [_kpi_card(*c, w=finding_card_w) for c in finding_cards]
    fc_row = Table([fc_cells], colWidths=[finding_card_w + 3] * 4)
    fc_row.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return _section("Estado de Hallazgos (Findings)", styles) + [fc_row]


def build_severity_section(styles, usable_w: float, stats_raw: dict) -> list:
    high_f   = int(stats_raw.get("high", 0))
    medium_f = int(stats_raw.get("medium", 0))
    low_f    = int(stats_raw.get("low", 0))

    total_sev = max(high_f + medium_f + low_f, 1)
    sev_col_w = [70, 50, 60, usable_w - 180]
    sev_rows  = []
    for label, count, clr, bg in [
        ("HIGH",   high_f,   RED,   colors.HexColor("#fff5f5")),
        ("MEDIUM", medium_f, AMBER, colors.HexColor("#fffbeb")),
        ("LOW",    low_f,    GREEN, colors.HexColor("#f0fdf4")),
    ]:
        pct_v = count / total_sev * 100
        sev_rows.append([
            Paragraph(f"<b>{label}</b>",
                      ParagraphStyle("sevlbl", fontSize=8, fontName="Helvetica-Bold",
                                     textColor=clr, leading=10)),
            Paragraph(f"<b>{count}</b>",
                      ParagraphStyle("sevcnt", fontSize=8, fontName="Helvetica-Bold",
                                     textColor=INK, leading=10)),
            Paragraph(_pct(pct_v), styles["td"]),
            _pct_bar(pct_v, clr, bar_w=sev_col_w[3] - 16),
        ])

    sev_tbl = Table(sev_rows, colWidths=sev_col_w)
    sev_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.HexColor("#fff5f5"), colors.HexColor("#fffbeb"), colors.HexColor("#f0fdf4")]),
        ("BOX",            (0, 0), (-1, -1), 0.4, BORDER),
        ("INNERGRID",      (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING",     (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 7),
        ("LEFTPADDING",    (0, 0), (-1, -1), 10),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return _section("Recuento de Findings por Severidad", styles) + [sev_tbl]


def build_top_findings_section(styles, usable_w: float, top_findings: list) -> list:
    if not top_findings:
        return []

    op_col_w  = [60, 85, 110, 65, usable_w - 320]
    op_header = [Paragraph(h, styles["th"]) for h in
                 ["Servicio", "Recurso", "Tipo", "Ahorro/mes", "Descripción"]]
    op_data   = [op_header]
    for f in top_findings:
        op_data.append([
            Paragraph(f.get("aws_service", ""), styles["td"]),
            Paragraph(str(f.get("resource_id", ""))[:30], styles["tds"]),
            Paragraph(f.get("finding_type", ""), styles["tds"]),
            Paragraph(_fmt_usd(f.get("estimated_monthly_savings", 0)), styles["td"]),
            Paragraph(str(f.get("message", ""))[:120], styles["tds"]),
        ])

    op_tbl = Table(op_data, colWidths=op_col_w, repeatRows=1)
    op_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("BACKGROUND",    (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BG_ALT]),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("GRID",          (0, 0), (-1, -1), 0.25, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("ALIGN",         (3, 0), (3, -1),  "RIGHT"),
    ]))
    return _section("Top 5 Oportunidades de Ahorro", styles) + [op_tbl]


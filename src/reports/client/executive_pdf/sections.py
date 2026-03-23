"""
EXECUTIVE PDF — SECTIONS
========================
Functions that build each visual section of the report.
Every function receives the pre-computed data and the
shared `styles` / `usable_w` values, then returns a list
of ReportLab flowables to be appended to `elements`.
"""

import os
from datetime import datetime

from reportlab.platypus import Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

from .styles import (
    INK, MUTED, BORDER, BG_ALT, WHITE, DARK, ACCENT,
    GREEN, RED, AMBER, RISK_COLOR,
    _kpi_card, _section, _pct_bar, _fmt_usd, _pct,
)


# =====================================================
#   HEADER  (logo + title + date)
# =====================================================
def build_header(styles, usable_w: float) -> list:
    logo_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "assets", "logos", "logoFinopsLatam.png"
    )
    logo = Image(logo_path, width=100, height=33) if os.path.exists(logo_path) else Spacer(100, 33)

    header_data = [[
        logo,
        Table(
            [
                [Paragraph(
                    "Resumen Ejecutivo FinOps",
                    ParagraphStyle("ht", fontSize=16, fontName="Helvetica-Bold", textColor=DARK),
                )],
                [Paragraph(
                    f"Generado: {datetime.utcnow().strftime('%d de %B de %Y — %H:%M UTC')}",
                    ParagraphStyle("hd", fontSize=8, textColor=MUTED),
                )],
            ],
            colWidths=[usable_w - 120],
        ),
    ]]
    header_tbl = Table(header_data, colWidths=[120, usable_w - 120])
    header_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [
        header_tbl,
        HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10, spaceBefore=6),
    ]


# =====================================================
#   GENERAL INFO  (plan / accounts / users)
# =====================================================
def build_info_row(styles, plan: str, accounts: int, account_label: str, users: int) -> list:
    info_data = [[
        Paragraph("<b>Plan</b>",        styles["td"]), Paragraph(plan, styles["td"]),
        Paragraph("<b>Cuentas AWS</b>", styles["td"]), Paragraph(f"{accounts}  ({account_label})", styles["td"]),
        Paragraph("<b>Usuarios</b>",    styles["td"]), Paragraph(str(users), styles["td"]),
    ]]
    info_col_w = [70, 100, 90, 120, 55, 30]
    info_tbl = Table(info_data, colWidths=info_col_w)
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BG_ALT),
        ("BOX",           (0, 0), (-1, -1), 0.4, BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    return [info_tbl]


# =====================================================
#   FINANCIAL KPIs  (2 rows × 3 cards)
# =====================================================
def build_financial_kpis(styles, usable_w: float, cost_data: dict) -> list:
    prev_month_cost   = cost_data.get("previous_month_cost", 0)
    curr_partial      = cost_data.get("current_month_partial", 0)
    prev_year_cost    = cost_data.get("previous_year_cost", 0)
    curr_year_ytd     = cost_data.get("current_year_ytd", 0)
    potential_savings = cost_data.get("potential_savings", 0)
    annual_savings    = cost_data.get("annual_estimated_savings", 0)
    savings_pct       = cost_data.get("savings_percentage", 0)

    card_w = (usable_w - 16) / 3

    def _row(cards):
        cells = [_kpi_card(*c, w=card_w) for c in cards]
        t = Table([cells], colWidths=[card_w + 5] * 3)
        t.setStyle(TableStyle([
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    elements = _section("Resumen Financiero", styles)
    elements.append(_row([
        ("Gasto Mes Anterior",      _fmt_usd(prev_month_cost),  "Mes cerrado",                    "#eff6ff", "#1d4ed8"),
        ("Gasto Mes Actual (YTD)",  _fmt_usd(curr_partial),     "Parcial mes en curso",           "#f0fdf4", "#15803d"),
        ("Ahorro Mensual Acumulado", _fmt_usd(potential_savings), _pct(savings_pct) + " del gasto", "#ecfdf5", "#059669"),
    ]))
    elements.append(Spacer(1, 4))
    elements.append(_row([
        ("Gasto Año Anterior",      _fmt_usd(prev_year_cost), "Año fiscal anterior",              "#f5f3ff", "#6d28d9"),
        ("Gasto Año Actual (YTD)",  _fmt_usd(curr_year_ytd),  "Acumulado año en curso",           "#faf5ff", "#7c3aed"),
        ("Ahorro Anual Estimado",   _fmt_usd(annual_savings),  "Basado en findings activos",      "#fff7ed", "#c2410c"),
    ]))
    return elements


# =====================================================
#   FINDINGS SUMMARY CARDS  (1 row × 4 cards)
# =====================================================
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


# =====================================================
#   SEVERITY BREAKDOWN  (bar chart table)
# =====================================================
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


# =====================================================
#   GOVERNANCE & RISK
# =====================================================
def build_governance_section(
    styles, usable_w: float,
    compliance: float, risk_level: str, est_savings: float,
) -> list:
    card_w   = (usable_w - 16) / 3
    risk_col = RISK_COLOR.get(risk_level, MUTED)  # noqa: F841 — kept for parity

    gov_cards = [
        (
            "Cumplimiento (Compliance)", _pct(compliance),
            "Óptimo ≥80%  ·  Atención ≥50%  ·  Crítico <50%",
            "#eff6ff" if compliance >= 80 else "#fef2f2",
            "#1d4ed8" if compliance >= 80 else "#dc2626",
        ),
        (
            "Nivel de Riesgo", risk_level,
            "LOW / MEDIUM / HIGH / CRITICAL",
            "#f0fdf4" if risk_level == "LOW" else ("#fef2f2" if risk_level in ("HIGH", "CRITICAL") else "#fffbeb"),
            "#15803d" if risk_level == "LOW" else ("#dc2626" if risk_level in ("HIGH", "CRITICAL") else "#b45309"),
        ),
        (
            "Ahorro Mensual de Findings", f"USD ${est_savings:.0f}",
            "Oportunidades con inventario activo",
            "#f0fdf4", "#059669",
        ),
    ]
    gw_cells = [_kpi_card(lbl, val, sub, bg, fg, card_w) for lbl, val, sub, bg, fg in gov_cards]
    gw_row = Table([gw_cells], colWidths=[card_w + 5] * 3)
    gw_row.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return _section("Gobernanza & Riesgo", styles) + [gw_row]


# =====================================================
#   COST TREND  (last 6 months)
# =====================================================
def build_cost_trend_section(styles, usable_w: float, monthly_cost: list) -> list:
    if not monthly_cost:
        return []

    mc_6      = monthly_cost[-6:]
    total_mc  = sum(float(m["amount"]) for m in mc_6) or 1
    bar_col_w = usable_w - 235
    mc_header = [Paragraph(h, styles["th"]) for h in ["Mes", "Gasto", "% del Total", "Barra"]]
    mc_data   = [mc_header]

    for m in mc_6:
        pct_val = float(m["amount"]) / total_mc * 100
        mc_data.append([
            Paragraph(str(m["month"]), styles["td"]),
            Paragraph(_fmt_usd(m["amount"]), styles["td"]),
            Paragraph(_pct(pct_val), styles["td"]),
            _pct_bar(pct_val, ACCENT, bar_w=bar_col_w - 16),
        ])

    mc_tbl = Table(mc_data, colWidths=[80, 85, 70, bar_col_w], repeatRows=1)
    mc_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("BACKGROUND",    (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BG_ALT]),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("GRID",          (0, 0), (-1, -1), 0.25, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return _section("Tendencia de Costos — Últimos 6 Meses", styles) + [mc_tbl]


# =====================================================
#   TOP 5 SAVINGS OPPORTUNITIES
# =====================================================
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


# =====================================================
#   SERVICE COST BREAKDOWN
# =====================================================
def build_service_breakdown_section(styles, usable_w: float, service_bkdn: list) -> list:
    if not service_bkdn:
        return []

    total_svc  = sum(float(s.get("amount", 0)) for s in service_bkdn) or 1
    svc_bar_w  = usable_w - 345
    svc_col_w  = [185, 85, 75, svc_bar_w]
    svc_header = [Paragraph(h, styles["th"])
                  for h in ["Servicio", "Costo mensual", "Porcentaje", ""]]
    svc_data   = [svc_header]
    for s in service_bkdn:
        pct_svc = float(s.get("amount", 0)) / total_svc * 100
        svc_data.append([
            Paragraph(s.get("service", ""), styles["td"]),
            Paragraph(_fmt_usd(s.get("amount", 0)), styles["td"]),
            Paragraph(_pct(pct_svc), styles["td"]),
            _pct_bar(pct_svc, ACCENT, bar_w=svc_bar_w - 16),
        ])

    # total row
    svc_data.append([
        Paragraph("<b>Total</b>",             styles["td"]),
        Paragraph(f"<b>{_fmt_usd(total_svc)}</b>", styles["td"]),
        Paragraph("<b>100%</b>",              styles["td"]),
        Paragraph("",                         styles["td"]),
    ])

    svc_tbl = Table(svc_data, colWidths=svc_col_w, repeatRows=1)
    svc_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0),  (-1, 0),  DARK),
        ("TEXTCOLOR",     (0, 0),  (-1, 0),  WHITE),
        ("BACKGROUND",    (0, 1),  (-1, -2), WHITE),
        ("ROWBACKGROUNDS",(0, 1),  (-1, -2), [WHITE, BG_ALT]),
        ("BACKGROUND",    (0, -1), (-1, -1), BG_ALT),
        ("FONTNAME",      (0, 1),  (-1, -1), "Helvetica"),
        ("GRID",          (0, 0),  (-1, -1), 0.25, BORDER),
        ("TOPPADDING",    (0, 0),  (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0),  (-1, -1), 6),
        ("LEFTPADDING",   (0, 0),  (-1, -1), 8),
        ("VALIGN",        (0, 0),  (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0),  (2, -1),  "RIGHT"),
    ]))
    return _section("Distribución de Costos por Servicio (Mes Actual)", styles) + [svc_tbl]


# =====================================================
#   FOOTER
# =====================================================
def build_footer(styles) -> list:
    from reportlab.platypus import HRFlowable
    return [
        Spacer(1, 14),
        HRFlowable(width="100%", thickness=0.4, color=BORDER),
        Paragraph(
            "FinOpsLatam — Plataforma de Optimización Financiera para AWS  ·  "
            "contacto@finopslatam.com  ·  Confidencial",
            ParagraphStyle("footer", fontSize=7, textColor=MUTED, alignment=1, leading=10),
        ),
    ]

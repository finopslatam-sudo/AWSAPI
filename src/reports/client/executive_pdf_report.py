"""
EXECUTIVE PDF REPORT
====================
Resumen Ejecutivo FinOps — A4 Portrait
Diseñado para presentaciones ejecutivas y stakeholders.
"""

import os
from io import BytesIO
from datetime import datetime

from reportlab.platypus import (
    Paragraph, Spacer, Image, Table, TableStyle, SimpleDocTemplate, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors

from src.services.client_dashboard_service import ClientDashboardService
from src.services.client_stats_service import get_users_by_client, get_client_plan
from src.services.client_findings_service import ClientFindingsService
from src.models.aws_account import AWSAccount
from src.services.dashboard.governance_service import GovernanceService
from src.services.dashboard.risk_service import RiskService

# =====================================================
#   PALETTE
# =====================================================
INK     = colors.HexColor("#0f172a")
MUTED   = colors.HexColor("#64748b")
BORDER  = colors.HexColor("#e2e8f0")
BG_ALT  = colors.HexColor("#f8fafc")
WHITE   = colors.white
DARK    = colors.HexColor("#1e293b")
ACCENT  = colors.HexColor("#2563eb")
GREEN   = colors.HexColor("#16a34a")
RED     = colors.HexColor("#dc2626")
AMBER   = colors.HexColor("#d97706")
INDIGO  = colors.HexColor("#4f46e5")

RISK_COLOR = {
    "LOW":      colors.HexColor("#16a34a"),
    "MEDIUM":   colors.HexColor("#d97706"),
    "HIGH":     colors.HexColor("#dc2626"),
    "CRITICAL": colors.HexColor("#9f1239"),
}


def _fmt_usd(value) -> str:
    v = float(value or 0)
    if v >= 1000:
        return f"USD ${v/1000:.1f}K"
    return f"USD ${v:.2f}"


def _pct(value) -> str:
    return f"{float(value or 0):.1f}%"


# =====================================================
#   KPI CARD (celda de tabla simulando card)
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
#   BUILD EXECUTIVE PDF
# =====================================================
def build_executive_pdf(client_id: int, aws_account_id: int | None = None) -> bytes:

    # ── datos ──────────────────────────────────────────────
    cost_data   = ClientDashboardService.get_cost_data(client_id, aws_account_id)
    stats_raw   = ClientFindingsService.get_stats(client_id, aws_account_id)
    plan        = get_client_plan(client_id) or "Sin plan activo"
    users       = get_users_by_client(client_id)
    accounts    = AWSAccount.query.filter_by(client_id=client_id, is_active=True).count()

    # top 5 oportunidades (mayor ahorro)
    top_findings = ClientFindingsService.list_findings(
        client_id=client_id,
        page=1, per_page=5,
        status="active",
        severity=None,
        finding_type=None,
        service=None, region=None, search=None,
        sort_by="estimated_monthly_savings",
        sort_order="desc",
    ).get("data", [])

    # governance y riesgo
    try:
        gov  = GovernanceService.get_governance_score(client_id, aws_account_id)
        risk = RiskService.get_risk_profile(client_id, aws_account_id)
    except Exception:
        gov  = {"compliance_percentage": 0}
        risk = {"risk_level": "N/A", "risk_score": 0}

    # extraer KPIs financieros
    prev_month_cost  = cost_data.get("previous_month_cost", 0)
    curr_partial     = cost_data.get("current_month_partial", 0)
    prev_year_cost   = cost_data.get("previous_year_cost", 0)
    curr_year_ytd    = cost_data.get("current_year_ytd", 0)
    potential_savings = cost_data.get("potential_savings", 0)
    annual_savings   = cost_data.get("annual_estimated_savings", 0)
    savings_pct      = cost_data.get("savings_percentage", 0)
    monthly_cost     = cost_data.get("monthly_cost", [])
    service_bkdn     = sorted(
        cost_data.get("service_breakdown", []),
        key=lambda x: float(x.get("amount", 0)),
        reverse=True
    )[:8]

    # findings
    total_f     = int(stats_raw.get("total", 0))
    active_f    = int(stats_raw.get("active", 0))
    resolved_f  = int(stats_raw.get("resolved", 0))
    high_f      = int(stats_raw.get("high", 0))
    medium_f    = int(stats_raw.get("medium", 0))
    low_f       = int(stats_raw.get("low", 0))
    est_savings = float(stats_raw.get("estimated_monthly_savings", 0))

    compliance  = float(gov.get("compliance_percentage", 0))
    risk_level  = str(risk.get("risk_level", "N/A")).upper()
    risk_col    = RISK_COLOR.get(risk_level, MUTED)

    # ── documento ──────────────────────────────────────────
    buffer = BytesIO()
    margin = 1.8 * cm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    usable_w = A4[0] - 2 * margin   # ~453 pt

    # ── estilos ────────────────────────────────────────────
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

    elements = []

    # ── CABECERA (logo + título) ────────────────────────────
    logo_path = os.path.join(
        os.path.dirname(__file__), "..", "assets", "logos", "logoFinopsLatam.png"
    )
    logo = Image(logo_path, width=100, height=33) if os.path.exists(logo_path) else Spacer(100, 33)

    header_data = [[
        logo,
        Table(
            [
                [Paragraph("Resumen Ejecutivo FinOps",
                           ParagraphStyle("ht", fontSize=16, fontName="Helvetica-Bold", textColor=DARK))],
                [Paragraph(f"Generado: {datetime.utcnow().strftime('%d de %B de %Y — %H:%M UTC')}",
                           ParagraphStyle("hd", fontSize=8, textColor=MUTED))],
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
    elements.append(header_tbl)
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10, spaceBefore=6))

    # ── INFO GENERAL ───────────────────────────────────────
    account_label = "Todas las cuentas"
    if aws_account_id:
        acc = AWSAccount.query.get(aws_account_id)
        account_label = acc.account_name if acc else str(aws_account_id)

    info_data = [
        [
            Paragraph("<b>Plan</b>",    styles["td"]), Paragraph(plan, styles["td"]),
            Paragraph("<b>Cuentas AWS</b>", styles["td"]), Paragraph(f"{accounts}  ({account_label})", styles["td"]),
            Paragraph("<b>Usuarios</b>", styles["td"]), Paragraph(str(users), styles["td"]),
        ]
    ]
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
    elements.append(info_tbl)

    # ── KPIs FINANCIEROS (2 filas × 3 cards) ───────────────
    elements += _section("Resumen Financiero", styles)

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

    elements.append(_row([
        ("Gasto Mes Anterior",    _fmt_usd(prev_month_cost),  "Mes cerrado",          "#eff6ff", "#1d4ed8"),
        ("Gasto Mes Actual (YTD)", _fmt_usd(curr_partial),    "Parcial mes en curso", "#f0fdf4", "#15803d"),
        ("Ahorro Mensual Acumulado", _fmt_usd(potential_savings), _pct(savings_pct) + " del gasto", "#ecfdf5", "#059669"),
    ]))
    elements.append(Spacer(1, 4))
    elements.append(_row([
        ("Gasto Año Anterior",    _fmt_usd(prev_year_cost),  "Año fiscal anterior",  "#f5f3ff", "#6d28d9"),
        ("Gasto Año Actual (YTD)", _fmt_usd(curr_year_ytd),  "Acumulado año en curso","#faf5ff", "#7c3aed"),
        ("Ahorro Anual Estimado", _fmt_usd(annual_savings),  "Basado en findings activos", "#fff7ed", "#c2410c"),
    ]))

    # ── HALLAZGOS (2 filas × 4 cards) ──────────────────────
    elements += _section("Estado de Hallazgos (Findings)", styles)

    finding_card_w = (usable_w - 12) / 4
    finding_cards = [
        ("Total Findings",     str(total_f),       "Detectados",                     "#f8fafc", "#334155"),
        ("Activos",            str(active_f),       "Requieren acción",               "#fef2f2", "#dc2626"),
        ("Resueltos",          str(resolved_f),     "Optimizaciones aplicadas",       "#f0fdf4", "#16a34a"),
        ("Alta Severidad",     str(high_f),         "Prioridad inmediata",            "#fff7ed", "#ea580c"),
    ]
    fc_cells = [_kpi_card(*c, w=finding_card_w) for c in finding_cards]
    fc_row = Table([fc_cells], colWidths=[finding_card_w + 3] * 4)
    fc_row.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(fc_row)

    # ── GOVERNANCE & RISK ──────────────────────────────────
    elements += _section("Gobernanza & Riesgo", styles)

    gov_cards = [
        ("Cumplimiento (Compliance)", _pct(compliance),
         "Óptimo ≥80%  ·  Atención ≥50%  ·  Crítico <50%",
         "#eff6ff" if compliance >= 80 else "#fef2f2",
         "#1d4ed8" if compliance >= 80 else "#dc2626"),
        ("Nivel de Riesgo", risk_level,
         "LOW / MEDIUM / HIGH / CRITICAL",
         "#f0fdf4" if risk_level == "LOW" else ("#fef2f2" if risk_level in ("HIGH", "CRITICAL") else "#fffbeb"),
         "#15803d" if risk_level == "LOW" else ("#dc2626" if risk_level in ("HIGH", "CRITICAL") else "#b45309")),
        ("Ahorro Mensual de Findings", f"USD ${est_savings:.0f}",
         "Oportunidades con inventario activo",
         "#f0fdf4", "#059669"),
    ]
    gw_cells = [_kpi_card(lbl, val, sub, bg, fg, card_w) for lbl, val, sub, bg, fg in gov_cards]
    gw_row = Table([gw_cells], colWidths=[card_w + 5] * 3)
    gw_row.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(gw_row)

    # ── TENDENCIA DE COSTOS (últimos 6 meses) ──────────────
    if monthly_cost:
        elements += _section("Tendencia de Costos — Últimos 6 Meses", styles)

        total_mc = sum(float(m["amount"]) for m in monthly_cost) or 1
        mc_header = [Paragraph(h, styles["th"]) for h in ["Mes", "Gasto", "% del Total", "Barra"]]
        mc_data = [mc_header]

        for m in monthly_cost[-6:]:
            pct_val = float(m["amount"]) / total_mc * 100
            bar_filled = max(1, int(pct_val / 100 * 30))
            bar = "█" * bar_filled + "░" * (30 - bar_filled)
            mc_data.append([
                Paragraph(str(m["month"]), styles["td"]),
                Paragraph(_fmt_usd(m["amount"]), styles["td"]),
                Paragraph(_pct(pct_val), styles["td"]),
                Paragraph(bar, ParagraphStyle("bar", fontSize=6, textColor=ACCENT, fontName="Helvetica")),
            ])

        mc_tbl = Table(mc_data, colWidths=[80, 85, 70, usable_w - 235], repeatRows=1)
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
        elements.append(mc_tbl)

    # ── TOP 5 OPORTUNIDADES DE AHORRO ──────────────────────
    if top_findings:
        elements += _section("Top 5 Oportunidades de Ahorro", styles)

        op_col_w = [60, 85, 110, 65, usable_w - 320]
        op_header = [Paragraph(h, styles["th"]) for h in
                     ["Servicio", "Recurso", "Tipo", "Ahorro/mes", "Descripción"]]
        op_data = [op_header]
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
        elements.append(op_tbl)

    # ── DISTRIBUCIÓN POR SERVICIO ───────────────────────────
    if service_bkdn:
        elements += _section("Distribución de Costos por Servicio (Mes Actual)", styles)

        total_svc = sum(float(s.get("amount", 0)) for s in service_bkdn) or 1
        svc_header = [Paragraph(h, styles["th"]) for h in ["Servicio", "Costo", "Porcentaje"]]
        svc_data = [svc_header]
        for s in service_bkdn:
            pct_svc = float(s.get("amount", 0)) / total_svc * 100
            svc_data.append([
                Paragraph(s.get("service", ""), styles["td"]),
                Paragraph(_fmt_usd(s.get("amount", 0)), styles["td"]),
                Paragraph(_pct(pct_svc), styles["td"]),
            ])

        svc_col_w = [250, 100, 100]
        svc_tbl = Table(svc_data, colWidths=svc_col_w, repeatRows=1)
        svc_tbl.setStyle(TableStyle([
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
            ("ALIGN",         (1, 0), (2, -1),  "RIGHT"),
        ]))
        elements.append(svc_tbl)

    # ── PIE DE PÁGINA ──────────────────────────────────────
    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width="100%", thickness=0.4, color=BORDER))
    elements.append(Paragraph(
        "FinOpsLatam — Plataforma de Optimización Financiera para AWS  ·  contacto@finopslatam.com  ·  Confidencial",
        ParagraphStyle("footer", fontSize=7, textColor=MUTED, alignment=1, leading=10),
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

"""
RISK & COMPLIANCE PDF REPORT
============================
Reporte de Riesgo & Compliance — A4 Portrait
Evaluación de posicionamiento de riesgo del entorno cloud.
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
from src.services.dashboard.governance_service import GovernanceService
from src.services.dashboard.risk_service import RiskService
from src.models.aws_account import AWSAccount

# ── paleta ────────────────────────────────────────────────
INK    = colors.HexColor("#0f172a")
MUTED  = colors.HexColor("#64748b")
BORDER = colors.HexColor("#e2e8f0")
BG_ALT = colors.HexColor("#f8fafc")
WHITE  = colors.white
DARK   = colors.HexColor("#1e293b")
RED    = colors.HexColor("#dc2626")
AMBER  = colors.HexColor("#d97706")
GREEN  = colors.HexColor("#16a34a")
BLUE   = colors.HexColor("#1d4ed8")
ROSE   = colors.HexColor("#9f1239")

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


def _fmt_usd(v) -> str:
    v = float(v or 0)
    if v >= 1000:
        return f"USD ${v/1000:.1f}K"
    return f"USD ${v:.2f}"


def _pct(v) -> str:
    return f"{float(v or 0):.1f}%"


def _kpi(label, value, sub, bg_hex, fg_hex, w):
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


def _bar_cell(pct: float, bar_total_w: float, bar_color, bg_color) -> Table:
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


def _section(title, styles):
    return [
        Spacer(1, 10),
        Paragraph(title, styles["sec"]),
        HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6),
    ]


def _kpi_row(cards, usable_w):
    n = len(cards)
    w = (usable_w - 4 * (n - 1)) / n
    cells = [_kpi(*c, w=w) for c in cards]
    t = Table([cells], colWidths=[w + 4] * n)
    t.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def build_risk_pdf(client_id: int, aws_account_id: int | None = None) -> bytes:

    # ── datos ─────────────────────────────────────────────
    plan  = get_client_plan(client_id) or "Sin plan"
    users = get_users_by_client(client_id)
    acc_count = AWSAccount.query.filter_by(client_id=client_id, is_active=True).count()

    account_label = "Todas las cuentas"
    if aws_account_id:
        acc = AWSAccount.query.get(aws_account_id)
        account_label = acc.account_name if acc else str(aws_account_id)

    try:
        gov  = GovernanceService.get_governance_score(client_id, aws_account_id)
        risk = RiskService.get_risk_profile(client_id, aws_account_id)
        risk_bkdn = RiskService.get_risk_breakdown_by_service(client_id, aws_account_id)
    except Exception:
        gov  = {"compliance_percentage": 0}
        risk = {"risk_level": "N/A", "risk_score": 0, "high": 0, "medium": 0, "low": 0}
        risk_bkdn = []

    stats = ClientFindingsService.get_stats(client_id, aws_account_id)

    # hallazgos HIGH y CRITICAL para el detalle
    high_findings = ClientFindingsService.list_findings(
        client_id=client_id,
        page=1, per_page=20,
        status="active",
        severity="HIGH",
        finding_type=None,
        service=None, region=None, search=None,
        sort_by="created_at", sort_order="desc",
    ).get("data", [])

    compliance  = float(gov.get("compliance_percentage", 0))
    risk_level  = str(risk.get("risk_level", "N/A")).upper()
    risk_score  = float(risk.get("risk_score", 0))
    high_cnt    = int(risk.get("high", 0))
    medium_cnt  = int(risk.get("medium", 0))
    low_cnt     = int(risk.get("low", 0))
    total_f     = int(stats.get("total", 0))
    active_f    = int(stats.get("active", 0))
    resolved_f  = int(stats.get("resolved", 0))
    est_savings = float(stats.get("estimated_monthly_savings", 0))

    compliance_label = "Óptimo" if compliance >= 80 else ("Requiere atención" if compliance >= 50 else "Crítico")
    compliance_fg = "#16a34a" if compliance >= 80 else ("#d97706" if compliance >= 50 else "#dc2626")
    compliance_bg = "#f0fdf4" if compliance >= 80 else ("#fffbeb" if compliance >= 50 else "#fef2f2")

    # ── documento ─────────────────────────────────────────
    buffer = BytesIO()
    margin = 1.8 * cm
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=margin)
    usable_w = A4[0] - 2 * margin

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("sec", fontSize=10, fontName="Helvetica-Bold",
                              textColor=DARK, spaceBefore=4, spaceAfter=2))
    styles.add(ParagraphStyle("th", fontSize=8, fontName="Helvetica-Bold",
                              textColor=WHITE, leading=10))
    styles.add(ParagraphStyle("td", fontSize=8, textColor=INK, leading=10))
    styles.add(ParagraphStyle("tds", fontSize=7, textColor=MUTED, leading=9))

    el = []

    # ── CABECERA ─────────────────────────────────────────
    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "logos", "logoFinopsLatam.png")
    logo = Image(logo_path, width=100, height=33) if os.path.exists(logo_path) else Spacer(100, 33)

    hdr = Table([[
        logo,
        Table([
            [Paragraph("Reporte de Riesgo & Compliance — FinOpsLatam",
                       ParagraphStyle("ht", fontSize=14, fontName="Helvetica-Bold", textColor=DARK))],
            [Paragraph(f"Generado: {datetime.utcnow().strftime('%d de %B de %Y — %H:%M UTC')}",
                       ParagraphStyle("hd", fontSize=8, textColor=MUTED))],
        ], colWidths=[usable_w - 120]),
    ]], colWidths=[120, usable_w - 120])
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    el.append(hdr)
    el.append(HRFlowable(width="100%", thickness=1, color=RED, spaceAfter=10, spaceBefore=6))

    # ── INFO GENERAL ─────────────────────────────────────
    info = Table([[
        Paragraph("<b>Plan</b>", styles["td"]), Paragraph(plan, styles["td"]),
        Paragraph("<b>Cuentas AWS</b>", styles["td"]), Paragraph(f"{acc_count}  ({account_label})", styles["td"]),
        Paragraph("<b>Usuarios</b>", styles["td"]), Paragraph(str(users), styles["td"]),
    ]], colWidths=[65, 100, 85, 125, 50, 30])
    info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_ALT),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    el.append(info)

    # ── KPIs RIESGO & COMPLIANCE ──────────────────────────
    el += _section("Resumen de Riesgo & Compliance", styles)
    el.append(_kpi_row([
        ("Nivel de Riesgo",    risk_level,      "LOW / MEDIUM / HIGH / CRITICAL",
         RISK_BG.get(risk_level, "#f8fafc"), RISK_FG.get(risk_level, "#334155")),
        ("Score de Riesgo",    f"{risk_score:.0f}/100", "Mayor score = menor riesgo",
         "#eff6ff", "#1d4ed8"),
        ("Cumplimiento",       _pct(compliance),  compliance_label,
         compliance_bg, compliance_fg),
    ], usable_w))
    el.append(_kpi_row([
        ("Findings Alta Severidad", str(high_cnt),  "Requieren acción inmediata", "#fef2f2", "#dc2626"),
        ("Findings Medios",         str(medium_cnt), "Atención en el corto plazo", "#fffbeb", "#d97706"),
        ("Findings Bajos",          str(low_cnt),   "Monitorear",                 "#f0fdf4", "#16a34a"),
    ], usable_w))
    el.append(_kpi_row([
        ("Total Findings",    str(total_f),    "Detectados en el entorno",         "#f8fafc", "#334155"),
        ("Activos",           str(active_f),   "Pendientes de resolución",          "#fef2f2", "#dc2626"),
        ("Resueltos",         str(resolved_f), "Optimizaciones aplicadas",          "#f0fdf4", "#16a34a"),
    ], usable_w))

    # ── GRÁFICO DISTRIBUCIÓN POR SEVERIDAD ───────────────
    total_sev = (high_cnt + medium_cnt + low_cnt) or 1
    el += _section("Recuento de Findings por Severidad", styles)
    sev_data = [
        ("HIGH",   high_cnt,   colors.HexColor("#dc2626"), colors.HexColor("#e2e8f0"), colors.HexColor("#fef2f2")),
        ("MEDIUM", medium_cnt, colors.HexColor("#d97706"), colors.HexColor("#e2e8f0"), colors.HexColor("#fffbeb")),
        ("LOW",    low_cnt,    colors.HexColor("#16a34a"), colors.HexColor("#e2e8f0"), colors.HexColor("#f0fdf4")),
    ]
    bar_col_w     = usable_w - 100 - 70 - 70
    sev_cnt_style = ParagraphStyle("sc", fontSize=10, fontName="Helvetica-Bold", textColor=INK, leading=12)
    sev_pct_style = ParagraphStyle("sp", fontSize=9, textColor=MUTED, leading=11)
    sev_lbl_styles = {
        "HIGH":   ParagraphStyle("slh", fontSize=10, fontName="Helvetica-Bold", textColor=RED,   leading=12),
        "MEDIUM": ParagraphStyle("slm", fontSize=10, fontName="Helvetica-Bold", textColor=AMBER, leading=12),
        "LOW":    ParagraphStyle("sll", fontSize=10, fontName="Helvetica-Bold", textColor=GREEN, leading=12),
    }

    sev_tbl_rows = []
    for label, cnt, bar_col, bar_bg, row_bg in sev_data:
        pct_s    = cnt / total_sev * 100
        bar_cell = _bar_cell(pct_s, bar_col_w - 8, bar_col, bar_bg)
        sev_tbl_rows.append([
            Paragraph(label, sev_lbl_styles[label]),
            Paragraph(str(cnt), sev_cnt_style),
            Paragraph(f"{pct_s:.1f}%", sev_pct_style),
            bar_cell,
        ])

    sev_tbl = Table(sev_tbl_rows, colWidths=[100, 70, 70, bar_col_w])
    sev_tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",          (0, 0), (-1, -1), 0.25, BORDER),
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#fef2f2")),
        ("BACKGROUND",    (0, 1), (-1, 1),  colors.HexColor("#fffbeb")),
        ("BACKGROUND",    (0, 2), (-1, 2),  colors.HexColor("#f0fdf4")),
    ]))
    el.append(sev_tbl)

    # ── RIESGO POR SERVICIO ───────────────────────────────
    if risk_bkdn:
        el += _section("Riesgo por Servicio AWS", styles)
        rk_hdr = [Paragraph(h, styles["th"]) for h in
                  ["Servicio", "Total Recursos", "Alta Severidad", "Media", "Baja", "Score"]]
        rk_rows = [rk_hdr]
        for s in risk_bkdn[:15]:
            total_r = int(s.get("total_resources", 0))
            h_cnt = int(s.get("high", 0))
            m_cnt = int(s.get("medium", 0))
            l_cnt = int(s.get("low", 0))
            points = h_cnt * 5 + m_cnt * 3 + l_cnt
            score = round(100 - (points / max(total_r * 5, 1) * 100), 0)
            rk_rows.append([
                Paragraph(s.get("service_name", ""), styles["td"]),
                Paragraph(str(total_r), styles["td"]),
                Paragraph(str(h_cnt), ParagraphStyle("rh", fontSize=8, textColor=RED, leading=10)),
                Paragraph(str(m_cnt), ParagraphStyle("rm", fontSize=8, textColor=AMBER, leading=10)),
                Paragraph(str(l_cnt), ParagraphStyle("rl", fontSize=8, textColor=GREEN, leading=10)),
                Paragraph(f"{score:.0f}", styles["td"]),
            ])
        col_w = [170, 80, 70, 55, 55, 50]
        rk_tbl = Table(rk_rows, colWidths=col_w, repeatRows=1)
        rk_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BG_ALT]),
            ("GRID",          (0, 0), (-1, -1), 0.25, BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
            ("ALIGN",         (0, 0), (0, -1),  "LEFT"),
        ]))
        el.append(rk_tbl)

    # ── HALLAZGOS DE ALTA SEVERIDAD ───────────────────────
    if high_findings:
        el += _section("Hallazgos de Alta Severidad (Requieren Acción Inmediata)", styles)
        hf_hdr = [Paragraph(h, styles["th"]) for h in
                  ["Servicio", "Recurso", "Tipo", "Ahorro/mes", "Descripción"]]
        hf_rows = [hf_hdr]
        for f in high_findings[:10]:
            hf_rows.append([
                Paragraph(f.get("aws_service", ""), styles["td"]),
                Paragraph(str(f.get("resource_id", ""))[:28], styles["tds"]),
                Paragraph(f.get("finding_type", ""), styles["tds"]),
                Paragraph(_fmt_usd(f.get("estimated_monthly_savings", 0)), styles["td"]),
                Paragraph(str(f.get("message", ""))[:100], styles["tds"]),
            ])
        hf_col = [60, 85, 110, 65, usable_w - 320]
        hf_tbl = Table(hf_rows, colWidths=hf_col, repeatRows=1)
        hf_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#7f1d1d")),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, colors.HexColor("#fff5f5")]),
            ("GRID",          (0, 0), (-1, -1), 0.25, BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        el.append(hf_tbl)

    # ── PIE ──────────────────────────────────────────────
    el.append(Spacer(1, 14))
    el.append(HRFlowable(width="100%", thickness=0.4, color=BORDER))
    el.append(Paragraph(
        "FinOpsLatam — Plataforma de Optimización Financiera para AWS  ·  contacto@finopslatam.com  ·  Confidencial",
        ParagraphStyle("ft", fontSize=7, textColor=MUTED, alignment=1, leading=10),
    ))

    doc.build(el)
    buffer.seek(0)
    return buffer.getvalue()

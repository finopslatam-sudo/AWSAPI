"""Secciones del reporte PDF de Riesgo & Compliance."""

import os
from datetime import datetime

from reportlab.platypus import (
    Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

from src.reports.client.risk.styles import (
    INK, MUTED, BORDER, BG_ALT, WHITE, DARK, RED, AMBER, GREEN,
    RISK_FG, RISK_BG, fmt_usd, fmt_pct,
    kpi_row, section_header, bar_cell,
)


def build_header(usable_w, styles):
    logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "logos", "logoFinopsLatam.png")
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
    return [hdr, HRFlowable(width="100%", thickness=1, color=RED, spaceAfter=10, spaceBefore=6)]


def build_info_row(plan, acc_count, account_label, users, styles):
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
    return [info]


def build_kpi_section(risk_level, risk_score, compliance, compliance_label, compliance_fg,
                      compliance_bg, high_cnt, medium_cnt, low_cnt, total_f, active_f,
                      resolved_f, usable_w, styles):
    el = section_header("Resumen de Riesgo & Compliance", styles)
    el.append(kpi_row([
        ("Nivel de Riesgo", risk_level, "LOW / MEDIUM / HIGH / CRITICAL",
         RISK_BG.get(risk_level, "#f8fafc"), RISK_FG.get(risk_level, "#334155")),
        ("Score de Riesgo", f"{risk_score:.0f}/100", "Mayor score = menor riesgo", "#eff6ff", "#1d4ed8"),
        ("Cumplimiento", fmt_pct(compliance), compliance_label, compliance_bg, compliance_fg),
    ], usable_w))
    el.append(kpi_row([
        ("Findings Alta Severidad", str(high_cnt),   "Requieren acción inmediata", "#fef2f2", "#dc2626"),
        ("Findings Medios",         str(medium_cnt), "Atención en el corto plazo", "#fffbeb", "#d97706"),
        ("Findings Bajos",          str(low_cnt),    "Monitorear",                 "#f0fdf4", "#16a34a"),
    ], usable_w))
    el.append(kpi_row([
        ("Total Findings", str(total_f),    "Detectados en el entorno",  "#f8fafc", "#334155"),
        ("Activos",        str(active_f),   "Pendientes de resolución",  "#fef2f2", "#dc2626"),
        ("Resueltos",      str(resolved_f), "Optimizaciones aplicadas",  "#f0fdf4", "#16a34a"),
    ], usable_w))
    return el


def build_severity_chart(high_cnt, medium_cnt, low_cnt, usable_w, styles):
    total_sev = (high_cnt + medium_cnt + low_cnt) or 1
    el = section_header("Recuento de Findings por Severidad", styles)

    sev_data = [
        ("HIGH",   high_cnt,   colors.HexColor("#dc2626"), colors.HexColor("#e2e8f0"), colors.HexColor("#fef2f2")),
        ("MEDIUM", medium_cnt, colors.HexColor("#d97706"), colors.HexColor("#e2e8f0"), colors.HexColor("#fffbeb")),
        ("LOW",    low_cnt,    colors.HexColor("#16a34a"), colors.HexColor("#e2e8f0"), colors.HexColor("#f0fdf4")),
    ]
    bar_col_w = usable_w - 100 - 70 - 70
    sev_lbl_styles = {
        "HIGH":   ParagraphStyle("slh", fontSize=10, fontName="Helvetica-Bold", textColor=RED,   leading=12),
        "MEDIUM": ParagraphStyle("slm", fontSize=10, fontName="Helvetica-Bold", textColor=AMBER, leading=12),
        "LOW":    ParagraphStyle("sll", fontSize=10, fontName="Helvetica-Bold", textColor=GREEN, leading=12),
    }
    cnt_style = ParagraphStyle("sc", fontSize=10, fontName="Helvetica-Bold", textColor=INK, leading=12)
    pct_style = ParagraphStyle("sp", fontSize=9, textColor=MUTED, leading=11)

    rows = []
    for label, cnt, bar_col, bar_bg, row_bg in sev_data:
        pct_s = cnt / total_sev * 100
        rows.append([
            Paragraph(label, sev_lbl_styles[label]),
            Paragraph(str(cnt), cnt_style),
            Paragraph(f"{pct_s:.1f}%", pct_style),
            bar_cell(pct_s, bar_col_w - 8, bar_col, bar_bg),
        ])

    tbl = Table(rows, colWidths=[100, 70, 70, bar_col_w])
    tbl.setStyle(TableStyle([
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
    el.append(tbl)
    return el


def build_service_risk_section(risk_bkdn, styles):
    if not risk_bkdn:
        return []
    el = section_header("Riesgo por Servicio AWS", styles)
    hdr = [Paragraph(h, styles["th"]) for h in
           ["Servicio", "Total Recursos", "Alta Severidad", "Media", "Baja", "Score"]]
    rows = [hdr]
    for s in risk_bkdn[:15]:
        total_r = int(s.get("total_resources", 0))
        h_cnt = int(s.get("high", 0))
        m_cnt = int(s.get("medium", 0))
        l_cnt = int(s.get("low", 0))
        points = h_cnt * 5 + m_cnt * 3 + l_cnt
        score = round(100 - (points / max(total_r * 5, 1) * 100), 0)
        rows.append([
            Paragraph(s.get("service_name", ""), styles["td"]),
            Paragraph(str(total_r), styles["td"]),
            Paragraph(str(h_cnt), ParagraphStyle("rh", fontSize=8, textColor=RED, leading=10)),
            Paragraph(str(m_cnt), ParagraphStyle("rm", fontSize=8, textColor=AMBER, leading=10)),
            Paragraph(str(l_cnt), ParagraphStyle("rl", fontSize=8, textColor=GREEN, leading=10)),
            Paragraph(f"{score:.0f}", styles["td"]),
        ])
    tbl = Table(rows, colWidths=[170, 80, 70, 55, 55, 50], repeatRows=1)
    tbl.setStyle(TableStyle([
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
    el.append(tbl)
    return el


def build_high_findings_section(high_findings, usable_w, styles):
    if not high_findings:
        return []
    el = section_header("Hallazgos de Alta Severidad (Requieren Acción Inmediata)", styles)
    hdr = [Paragraph(h, styles["th"]) for h in
           ["Servicio", "Recurso", "Tipo", "Ahorro/mes", "Descripción"]]
    rows = [hdr]
    for f in high_findings[:10]:
        rows.append([
            Paragraph(f.get("aws_service", ""), styles["td"]),
            Paragraph(str(f.get("resource_id", ""))[:28], styles["tds"]),
            Paragraph(f.get("finding_type", ""), styles["tds"]),
            Paragraph(fmt_usd(f.get("estimated_monthly_savings", 0)), styles["td"]),
            Paragraph(str(f.get("message", ""))[:100], styles["tds"]),
        ])
    tbl = Table(rows, colWidths=[60, 85, 110, 65, usable_w - 320], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#7f1d1d")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, colors.HexColor("#fff5f5")]),
        ("GRID",          (0, 0), (-1, -1), 0.25, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    el.append(tbl)
    return el


def build_footer():
    from reportlab.lib.styles import ParagraphStyle as PS
    return [
        Spacer(1, 14),
        HRFlowable(width="100%", thickness=0.4, color=BORDER),
        Paragraph(
            "FinOpsLatam — Plataforma de Optimización Financiera para AWS  ·  contacto@finopslatam.com  ·  Confidencial",
            PS("ft", fontSize=7, textColor=MUTED, alignment=1, leading=10),
        ),
    ]

"""
COST PDF REPORT
===============
Reporte de Costos — A4 Portrait
Análisis financiero detallado para el cliente.
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
from src.models.aws_account import AWSAccount

# ── paleta ────────────────────────────────────────────────
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


def _section(title, styles):
    return [
        Spacer(1, 10),
        Paragraph(title, styles["sec"]),
        HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6),
    ]


def _bar_cell(pct: float, bar_total_w: float, bar_color, bg_color) -> Table:
    """Celda con barra de progreso embebida (para usar dentro de una Table)."""
    filled = max(2.0, pct / 100 * bar_total_w)
    empty  = max(0.0, bar_total_w - filled)
    if empty < 1:
        data, cw = [[""]], [bar_total_w]
    else:
        data, cw = [["", ""]], [filled, empty]
    t = Table(data, colWidths=cw, rowHeights=[7])
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


def _kpi_row(cards, col_w, usable_w):
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


def build_cost_pdf(client_id: int, aws_account_id: int | None = None) -> bytes:

    cost = ClientDashboardService.get_cost_data(client_id, aws_account_id)
    plan  = get_client_plan(client_id) or "Sin plan"
    users = get_users_by_client(client_id)
    acc_count = AWSAccount.query.filter_by(client_id=client_id, is_active=True).count()

    account_label = "Todas las cuentas"
    if aws_account_id:
        acc = AWSAccount.query.get(aws_account_id)
        account_label = acc.account_name if acc else str(aws_account_id)

    prev_month   = cost.get("previous_month_cost", 0)
    curr_partial = cost.get("current_month_partial", 0)
    prev_year    = cost.get("previous_year_cost", 0)
    curr_year    = cost.get("current_year_ytd", 0)
    savings      = cost.get("potential_savings", 0)
    ann_savings  = cost.get("annual_estimated_savings", 0)
    sav_pct      = cost.get("savings_percentage", 0)
    monthly      = cost.get("monthly_cost", [])
    svc          = sorted(cost.get("service_breakdown", []),
                          key=lambda x: float(x.get("amount", 0)), reverse=True)

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
            [Paragraph("Reporte de Costos — FinOpsLatam",
                       ParagraphStyle("ht", fontSize=15, fontName="Helvetica-Bold", textColor=DARK))],
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
    el.append(HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=10, spaceBefore=6))

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

    # ── KPIs FINANCIEROS ─────────────────────────────────
    el += _section("Resumen de Gastos", styles)
    el.append(_kpi_row([
        ("Gasto Mes Anterior",     _fmt_usd(prev_month),  "Mes cerrado",          "#eff6ff", "#1d4ed8"),
        ("Gasto Mes Actual (YTD)", _fmt_usd(curr_partial), "Parcial mes en curso", "#f0fdf4", "#15803d"),
        ("Ahorro Mensual Acumulado", _fmt_usd(savings),   _pct(sav_pct) + " del gasto", "#ecfdf5", "#059669"),
    ], [], usable_w))
    el.append(_kpi_row([
        ("Gasto Año Anterior",     _fmt_usd(prev_year),    "Año fiscal anterior",        "#f5f3ff", "#6d28d9"),
        ("Gasto Año Actual (YTD)", _fmt_usd(curr_year),    "Acumulado año en curso",     "#faf5ff", "#7c3aed"),
        ("Ahorro Anual Estimado",  _fmt_usd(ann_savings),  "Savings × 12 meses",         "#fff7ed", "#c2410c"),
    ], [], usable_w))

    # ── TENDENCIA MENSUAL ────────────────────────────────
    if monthly:
        el += _section("Tendencia de Costos — Últimos 6 Meses", styles)
        last6     = monthly[-6:]
        total_mc  = sum(float(m["amount"]) for m in last6) or 1
        max_mc    = max(float(m["amount"]) for m in last6) or 1
        bar_col_w = usable_w - 245   # ancho columna tendencia
        bar_fill  = colors.HexColor("#1d4ed8")
        bar_bg    = colors.HexColor("#dbeafe")
        hdr_row   = [Paragraph(h, styles["th"]) for h in
                     ["Mes", "Gasto", "% del Total", "Tendencia Visual"]]
        rows = [hdr_row]
        for m in last6:
            amt   = float(m["amount"])
            pct_v = amt / total_mc * 100
            ratio = amt / max_mc          # relativo al mes más caro
            bar_cell = _bar_cell(ratio * 100, bar_col_w - 10, bar_fill, bar_bg)
            rows.append([
                Paragraph(str(m["month"]), styles["td"]),
                Paragraph(_fmt_usd(amt), styles["td"]),
                Paragraph(_pct(pct_v), styles["td"]),
                bar_cell,
            ])
        tbl = Table(rows, colWidths=[80, 90, 75, bar_col_w], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  DARK),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BG_ALT]),
            ("GRID",          (0, 0), (-1, -1), 0.25, BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        el.append(tbl)

    # ── DISTRIBUCIÓN POR SERVICIO ─────────────────────────
    if svc:
        el += _section("Distribución de Costos por Servicio (Mes Actual)", styles)
        total_svc = sum(float(s.get("amount", 0)) for s in svc) or 1
        bar_w_svc = 130.0
        bar_fill_s = colors.HexColor("#1d4ed8")
        bar_bg_s   = colors.HexColor("#e2e8f0")
        pct_style  = ParagraphStyle("ps", fontSize=8, textColor=MUTED, leading=10)
        col_svc    = 210
        col_cost   = 90
        col_pct    = usable_w - col_svc - col_cost   # ~193

        svc_hdr = [Paragraph(h, styles["th"]) for h in
                   ["Servicio", "Costo mensual", "Porcentaje"]]
        svc_rows = [svc_hdr]
        for s in svc:
            amt   = float(s.get("amount", 0))
            pct_s = amt / total_svc * 100
            bar_table = Table(
                [[_bar_cell(pct_s, bar_w_svc, bar_fill_s, bar_bg_s),
                  Paragraph(f"{pct_s:.2f}%", pct_style)]],
                colWidths=[bar_w_svc, col_pct - bar_w_svc - 4],
            )
            bar_table.setStyle(TableStyle([
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ]))
            svc_rows.append([
                Paragraph(s.get("service", ""), styles["td"]),
                Paragraph(_fmt_usd(amt), styles["td"]),
                bar_table,
            ])
        # fila de total
        svc_rows.append([
            Paragraph("<b>Total</b>", styles["td"]),
            Paragraph(f"<b>{_fmt_usd(total_svc)}</b>", styles["td"]),
            Paragraph("<b>100%</b>", styles["td"]),
        ])
        n_data = len(svc_rows)
        svc_tbl = Table(svc_rows, colWidths=[col_svc, col_cost, col_pct], repeatRows=1)
        svc_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0),          (-1, 0),           DARK),
            ("TEXTCOLOR",     (0, 0),          (-1, 0),           WHITE),
            ("ROWBACKGROUNDS",(0, 1),          (-1, n_data - 2),  [WHITE, BG_ALT]),
            ("BACKGROUND",    (0, n_data - 1), (-1, n_data - 1),  colors.HexColor("#f1f5f9")),
            ("GRID",          (0, 0),          (-1, -1),          0.25, BORDER),
            ("TOPPADDING",    (0, 0),          (-1, -1),          6),
            ("BOTTOMPADDING", (0, 0),          (-1, -1),          6),
            ("LEFTPADDING",   (0, 0),          (-1, -1),          8),
            ("VALIGN",        (0, 0),          (-1, -1),          "MIDDLE"),
            ("FONTNAME",      (0, n_data - 1), (-1, n_data - 1),  "Helvetica-Bold"),
        ]))
        el.append(svc_tbl)

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

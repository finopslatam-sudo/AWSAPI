"""Secciones de costos para el PDF ejecutivo."""

from reportlab.platypus import Paragraph, Table, TableStyle

from .styles import ACCENT, DARK, WHITE, BG_ALT, BORDER, _section, _fmt_usd, _pct, _pct_bar


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


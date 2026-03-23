"""KPIs financieros del PDF ejecutivo."""

from reportlab.platypus import Table, TableStyle, Spacer

from .styles import _kpi_card, _section, _fmt_usd, _pct


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

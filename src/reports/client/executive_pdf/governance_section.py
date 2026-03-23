"""Sección de gobernanza y riesgo."""

from reportlab.platypus import Table, TableStyle

from .styles import RISK_COLOR, MUTED, _kpi_card, _section, _pct


def build_governance_section(styles, usable_w: float,
                             compliance: float, risk_level: str, est_savings: float) -> list:
    card_w   = (usable_w - 16) / 3
    _ = RISK_COLOR.get(risk_level, MUTED)  # kept for parity / potential styling

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

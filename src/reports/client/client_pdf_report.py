"""
CLIENT PDF REPORT
=================

Genera el reporte PDF visible para un cliente FinOpsLatam.

- No contiene métricas globales
- No expone datos de otros clientes
- Consume datos del client_stats_provider
"""

from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

from src.reports.exporters.pdf_base import build_pdf


def build_client_pdf(stats: dict) -> bytes:
    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph("Reporte de Cliente – FinOpsLatam", styles["Title"])
    )
    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            f"Generado: {datetime.utcnow().strftime('%d-%m-%Y %H:%M UTC')}",
            styles["Normal"]
        )
    )
    elements.append(Spacer(1, 20))

    plan = stats.get("plan") or "Sin plan activo"

    elements.append(
        Paragraph(f"Plan contratado: {plan}", styles["Normal"])
    )
    elements.append(
        Paragraph(f"Usuarios asociados: {stats['user_count']}", styles["Normal"])
    )
    elements.append(
        Paragraph(f"Servicios activos: {stats['active_services']}", styles["Normal"])
    )

    return build_pdf(elements)

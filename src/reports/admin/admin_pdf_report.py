from reportlab.platypus import Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime

from src.reports.exporters.pdf_base import build_pdf
from src.reports.charts.admin_charts import generate_users_by_plan_chart

def build_admin_pdf(stats: dict) -> bytes:
    styles = getSampleStyleSheet()
    elements = []

    # Título
    elements.append(
        Paragraph("Reporte Administrativo FinOpsLatam", styles["Title"])
    )
    elements.append(Spacer(1, 12))

    # Fecha
    elements.append(
        Paragraph(
            f"Generado: {datetime.utcnow().strftime('%d-%m-%Y %H:%M UTC')}",
            styles["Normal"]
        )
    )
    elements.append(Spacer(1, 20))

    # KPIs
    elements.append(Paragraph(f"Usuarios totales: {stats['total_users']}", styles["Normal"]))
    elements.append(Paragraph(f"Usuarios activos: {stats['active_users']}", styles["Normal"]))
    elements.append(Paragraph(f"Usuarios inactivos: {stats['inactive_users']}", styles["Normal"]))
    elements.append(Spacer(1, 16))

    # Tabla planes
    table_data = [["Plan", "Cantidad"]]
    for item in stats["users_by_plan"]:
        table_data.append([item["plan"], item["count"]])

    table = Table(table_data, colWidths=[10 * 28.35, 3 * 28.35])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONT", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Gráfico
    chart_path = generate_users_by_plan_chart(stats)
    elements.append(Image(chart_path, width=12 * 28.35, height=6 * 28.35))

    return build_pdf(elements)

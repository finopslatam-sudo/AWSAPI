from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
import matplotlib.pyplot as plt
import tempfile
import os
from datetime import datetime


def build_admin_pdf(stats: dict) -> bytes:
    buffer = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(
        buffer.name,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    story = []

    # =====================================================
    # LOGO
    # =====================================================
    logo_path = os.path.join(
        os.getcwd(), "app", "public", "logo2.png"
    )

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=4 * cm, height=4 * cm)
        story.append(logo)

    story.append(Spacer(1, 12))

    # =====================================================
    # TITLE
    # =====================================================
    story.append(
        Paragraph(
            "<b>Reporte Administrativo – FinOpsLatam</b>",
            styles["Title"],
        )
    )

    story.append(
        Paragraph(
            f"Generado el {datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')}",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 20))

    # =====================================================
    # KPIs
    # =====================================================
    kpi_table = Table(
        [
            ["Usuarios totales", stats["total_users"]],
            ["Usuarios activos", stats["active_users"]],
            ["Usuarios inactivos", stats["inactive_users"]],
        ],
        colWidths=[8 * cm, 4 * cm],
    )

    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ("FONT", (0, 0), (-1, -1), "Helvetica"),
            ]
        )
    )

    story.append(kpi_table)
    story.append(Spacer(1, 20))

    # =====================================================
    # CHART: USERS STATUS
    # =====================================================
    def render_pie(labels, values, filename):
        plt.figure(figsize=(4, 4))
        plt.pie(values, labels=labels, autopct="%1.1f%%")
        plt.title("Usuarios activos vs inactivos")
        plt.savefig(filename, bbox_inches="tight")
        plt.close()

    pie_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    render_pie(
        ["Activos", "Inactivos"],
        [stats["active_users"], stats["inactive_users"]],
        pie_path,
    )

    story.append(Image(pie_path, width=10 * cm, height=10 * cm))
    story.append(Spacer(1, 20))

    # =====================================================
    # CHART: USERS BY PLAN
    # =====================================================
    plans = [p["plan"] for p in stats["users_by_plan"]]
    counts = [p["count"] for p in stats["users_by_plan"]]

    bar_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name

    plt.figure(figsize=(6, 4))
    plt.bar(plans, counts)
    plt.xticks(rotation=30, ha="right")
    plt.title("Usuarios por plan")
    plt.tight_layout()
    plt.savefig(bar_path)
    plt.close()

    story.append(Image(bar_path, width=14 * cm, height=8 * cm))
    story.append(Spacer(1, 20))

    # =====================================================
    # TABLE: USERS BY PLAN
    # =====================================================
    table_data = [["Plan", "Cantidad"]]
    for p in stats["users_by_plan"]:
        table_data.append([p["plan"], p["count"]])

    plan_table = Table(table_data, colWidths=[10 * cm, 4 * cm])
    plan_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ]
        )
    )

    story.append(plan_table)
    story.append(Spacer(1, 30))

    # =====================================================
    # FOOTER LEGAL
    # =====================================================
    story.append(
        Paragraph(
            "© 2026 FinOpsLatam — Información confidencial. Uso exclusivo interno.",
            styles["Italic"],
        )
    )

    doc.build(story)

    with open(buffer.name, "rb") as f:
        pdf_bytes = f.read()

    return pdf_bytes

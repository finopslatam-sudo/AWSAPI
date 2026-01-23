from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
import matplotlib.pyplot as plt
import tempfile
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter


def build_admin_pdf(stats: dict) -> bytes:
    """
    Genera el PDF administrativo para ROOT / ADMIN.

    Reporte enfocado en CLIENTES y PLANES,
    no en usuarios individuales.
    """

    clients = stats.get("clients", [])

    total_clients = len(clients)
    active_clients = len([c for c in clients if c["is_active"]])
    inactive_clients = total_clients - active_clients

    plans_counter = Counter(
        c["plan"] or "Sin plan"
        for c in clients
    )

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
    # HEADER CORPORATIVO
    # =====================================================
    logo_path = os.path.join(
        os.getcwd(),
        "src",
        "assets",
        "logos",
        "logoFinopsLatam.png"
    )

    logo = (
        Image(logo_path, width=3.5 * cm, height=3.5 * cm)
        if os.path.exists(logo_path)
        else ""
    )

    title_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Title"],
        alignment=1,
        fontSize=18,
        spaceAfter=4,
    )

    date_style = ParagraphStyle(
        "HeaderDate",
        parent=styles["Normal"],
        alignment=2,
        fontSize=9,
        textColor=colors.grey,
    )

    chile_time = datetime.now(ZoneInfo("America/Santiago"))

    header_table = Table(
        [
            [
                logo,
                Paragraph("Reporte Administrativo<br/>FinOpsLatam", title_style),
                Paragraph(
                    f"Generado el<br/>{chile_time.strftime('%d/%m/%Y %H:%M CLT')}",
                    date_style,
                ),
            ]
        ],
        colWidths=[4 * cm, 9 * cm, 4 * cm],
    )

    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 20))

    # =====================================================
    # KPIs CLIENTES
    # =====================================================
    kpi_table = Table(
        [
            ["Clientes totales", total_clients],
            ["Clientes activos", active_clients],
            ["Clientes inactivos", inactive_clients],
        ],
        colWidths=[10 * cm, 4 * cm],
    )

    kpi_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(kpi_table)
    story.append(Spacer(1, 30))

    # =====================================================
    # GRÁFICO: CLIENTES POR PLAN
    # =====================================================
    labels = list(plans_counter.keys())
    values = list(plans_counter.values())

    pie_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name

    plt.figure(figsize=(5, 5))
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    plt.title("Clientes por plan")
    plt.axis("equal")
    plt.savefig(pie_path, bbox_inches="tight")
    plt.close()

    story.append(Image(pie_path, width=10 * cm, height=10 * cm))
    story.append(Spacer(1, 30))

    # =====================================================
    # TABLA: CLIENTES POR PLAN
    # =====================================================
    table_data = [["Plan", "Cantidad de clientes"]]
    for plan, count in plans_counter.items():
        table_data.append([plan, count])

    plan_table = Table(table_data, colWidths=[10 * cm, 4 * cm])
    plan_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(plan_table)
    story.append(Spacer(1, 40))

    # =====================================================
    # FOOTER
    # =====================================================
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        alignment=1,
        textColor=colors.grey,
    )

    story.append(
        Paragraph(
            "© 2026 FinOpsLatam — Información confidencial. Uso exclusivo interno.",
            footer_style,
        )
    )

    doc.build(story)

    with open(buffer.name, "rb") as f:
        return f.read()

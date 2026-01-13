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
        alignment=1,  # CENTER
        fontSize=18,
        spaceAfter=4,
    )

    date_style = ParagraphStyle(
        "HeaderDate",
        parent=styles["Normal"],
        alignment=2,  # RIGHT
        fontSize=9,
        textColor=colors.grey,
    )

    header_table = Table(
        [
            [
                logo,
                Paragraph("Reporte Administrativo<br/>FinOpsLatam", title_style),
                Paragraph(
                    f"Generado el<br/>{datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')}",
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

    # Línea separadora
    story.append(Spacer(1, 8))
    story.append(
        Table(
            [[""]],
            colWidths=[17 * cm],
            style=[("LINEBELOW", (0, 0), (-1, -1), 1, colors.lightgrey)],
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
        colWidths=[10 * cm, 4 * cm],
    )

    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONT", (0, 0), (-1, -1), "Helvetica"),
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
    # GRÁFICO: USUARIOS ACTIVOS VS INACTIVOS
    # =====================================================
    def render_pie(labels, values, filename):
        plt.figure(figsize=(4, 4))
        plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        plt.title("Usuarios activos vs inactivos")
        plt.axis("equal")
        plt.savefig(filename, bbox_inches="tight")
        plt.close()

    pie_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    render_pie(
        ["Activos", "Inactivos"],
        [stats["active_users"], stats["inactive_users"]],
        pie_path,
    )

    story.append(Image(pie_path, width=10 * cm, height=10 * cm))
    story.append(Spacer(1, 30))

    # =====================================================
    # GRÁFICO: USUARIOS POR PLAN
    # =====================================================
    plans = [p["plan"] for p in stats["users_by_plan"]]
    counts = [p["count"] for p in stats["users_by_plan"]]

    bar_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name

    plt.figure(figsize=(6, 4))
    plt.bar(plans, counts, color="#6366F1")
    plt.xticks(rotation=30, ha="right")
    plt.title("Usuarios por plan")
    plt.tight_layout()
    plt.savefig(bar_path)
    plt.close()

    story.append(Image(bar_path, width=14 * cm, height=8 * cm))
    story.append(Spacer(1, 25))

    # =====================================================
    # TABLA: USUARIOS POR PLAN
    # =====================================================
    table_data = [["Plan", "Cantidad"]]
    for p in stats["users_by_plan"]:
        table_data.append([p["plan"], p["count"]])

    plan_table = Table(table_data, colWidths=[10 * cm, 4 * cm])
    plan_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(plan_table)
    story.append(Spacer(1, 40))

    # =====================================================
    # FOOTER LEGAL
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
        pdf_bytes = f.read()

    return pdf_bytes

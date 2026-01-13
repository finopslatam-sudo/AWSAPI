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
from datetime import datetime
import matplotlib.pyplot as plt
import tempfile
import os


# =====================================================
# UTILS
# =====================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logos", "logoFinopsLatam.png")


# =====================================================
# PDF BUILDER
# =====================================================
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
    styles.add(
        ParagraphStyle(
            name="TitleCustom",
            fontSize=18,
            spaceAfter=12,
            alignment=0,
            textColor=colors.HexColor("#1f2937"),
        )
    )

    story = []

    # =====================================================
    # HEADER (LOGO + TITLE)
    # =====================================================
    header_table_data = []

    if os.path.exists(LOGO_PATH):
        logo = Image(LOGO_PATH, width=4 * cm, height=4 * cm)
        header_table_data.append(
            [
                logo,
                Paragraph(
                    "<b>Reporte Administrativo</b><br/>FinOpsLatam",
                    styles["TitleCustom"],
                ),
            ]
        )
    else:
        header_table_data.append(
            [
                "",
                Paragraph(
                    "<b>Reporte Administrativo – FinOpsLatam</b>",
                    styles["TitleCustom"],
                ),
            ]
        )

    header = Table(
        header_table_data,
        colWidths=[5 * cm, 11 * cm],
        style=[
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.lightgrey),
        ],
    )

    story.append(header)
    story.append(Spacer(1, 12))

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
        colWidths=[9 * cm, 4 * cm],
    )

    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONT", (0, 0), (-1, -1), "Helvetica"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ]
        )
    )

    story.append(kpi_table)
    story.append(Spacer(1, 24))

    # =====================================================
    # PIE CHART – STATUS
    # =====================================================
    def render_pie(labels, values, filename):
        plt.figure(figsize=(4, 4))
        plt.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=["#22c55e", "#ef4444"],
        )
        plt.title("Usuarios activos vs inactivos")
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

    pie_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    render_pie(
        ["Activos", "Inactivos"],
        [stats["active_users"], stats["inactive_users"]],
        pie_path,
    )

    story.append(Image(pie_path, width=9 * cm, height=9 * cm))
    story.append(Spacer(1, 24))

    # =====================================================
    # BAR CHART – USERS BY PLAN
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
    story.append(Spacer(1, 24))

    # =====================================================
    # TABLE – USERS BY PLAN
    # =====================================================
    table_data = [["Plan", "Cantidad"]]
    for p in stats["users_by_plan"]:
        table_data.append([p["plan"], p["count"]])

    plan_table = Table(table_data, colWidths=[10 * cm, 3 * cm])
    plan_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ]
        )
    )

    story.append(plan_table)
    story.append(Spacer(1, 30))

    # =====================================================
    # FOOTER
    # =====================================================
    story.append(
        Paragraph(
            "© 2026 FinOpsLatam — Información confidencial. Uso exclusivo interno.",
            ParagraphStyle(
                "Footer",
                fontSize=9,
                textColor=colors.grey,
                alignment=1,
            ),
        )
    )

    doc.build(story)

    with open(buffer.name, "rb") as f:
        pdf_bytes = f.read()

    return pdf_bytes

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm

import matplotlib.pyplot as plt
import tempfile
import os
from datetime import datetime


# =====================================================
# PATHS & ASSETS
# =====================================================
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))
)

LOGO_PATH = os.path.join(
    BASE_DIR,
    "assets",
    "logos",
    "logoFinopsLatam.png"
)


# =====================================================
# MAIN BUILDER
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
    story = []

    # =====================================================
    # HEADER — LOGO
    # =====================================================
    if os.path.exists(LOGO_PATH):
        logo = Image(LOGO_PATH, width=5 * cm, height=2 * cm)
        logo.hAlign = "LEFT"
        story.append(logo)

    story.append(Spacer(1, 12))

    # =====================================================
    # TITLE
    # =====================================================
    story.append(
        Paragraph(
            "<b>Reporte Administrativo — FinOpsLatam</b>",
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
    # KPIs TABLE
    # =====================================================
    kpi_table = Table(
        [
            ["Usuarios totales", stats.get("total_users", 0)],
            ["Usuarios activos", stats.get("active_users", 0)],
            ["Usuarios inactivos", stats.get("inactive_users", 0)],
        ],
        colWidths=[9 * cm, 4 * cm],
    )

    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONT", (0, 0), (-1, -1), "Helvetica"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )

    story.append(kpi_table)
    story.append(Spacer(1, 24))

    # =====================================================
    # CHART — USERS STATUS
    # =====================================================
    def render_pie(labels, values, filename):
        plt.figure(figsize=(4, 4))
        plt.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
        )
        plt.title("Usuarios activos vs inactivos")
        plt.tight_layout()
        plt.savefig(filename, dpi=120)
        plt.close()

    pie_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    render_pie(
        ["Activos", "Inactivos"],
        [
            stats.get("active_users", 0),
            stats.get("inactive_users", 0),
        ],
        pie_file.name,
    )

    story.append(Image(pie_file.name, width=9 * cm, height=9 * cm))
    story.append(Spacer(1, 24))

    # =====================================================
    # CHART — USERS BY PLAN
    # =====================================================
    plans = [p["plan"] for p in stats.get("users_by_plan", [])]
    counts = [p["count"] for p in stats.get("users_by_plan", [])]

    bar_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    plt.figure(figsize=(6, 4))
    plt.bar(plans, counts, color="#6366F1")
    plt.xticks(rotation=30, ha="right")
    plt.title("Usuarios por plan")
    plt.tight_layout()
    plt.savefig(bar_file.name, dpi=120)
    plt.close()

    story.append(Image(bar_file.name, width=14 * cm, height=7 * cm))
    story.append(Spacer(1, 24))

    # =====================================================
    # TABLE — USERS BY PLAN
    # =====================================================
    table_data = [["Plan", "Cantidad"]]
    for p in stats.get("users_by_plan", []):
        table_data.append([p["plan"], p["count"]])

    plan_table = Table(
        table_data,
        colWidths=[10 * cm, 3 * cm],
    )

    plan_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ]
        )
    )

    story.append(plan_table)
    story.append(Spacer(1, 36))

    # =====================================================
    # FOOTER — LEGAL
    # =====================================================
    footer_style = ParagraphStyle(
        "Footer",
        fontSize=8,
        textColor=colors.grey,
        alignment=1,
    )

    story.append(
        Paragraph(
            "© 2026 FinOpsLatam — Información confidencial. Uso exclusivo interno.",
            footer_style,
        )
    )

    # =====================================================
    # BUILD PDF
    # =====================================================
    doc.build(story)

    with open(buffer.name, "rb") as f:
        pdf_bytes = f.read()

    # Cleanup temp files
    try:
        os.unlink(buffer.name)
        os.unlink(pie_file.name)
        os.unlink(bar_file.name)
    except Exception:
        pass

    return pdf_bytes

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.drawing.image import Image as XLImage
from openpyxl.chart import PieChart, Reference, BarChart
from openpyxl.utils import get_column_letter
from datetime import datetime
from io import BytesIO
import os
import pytz


def build_admin_xlsx(stats: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte Administrativo"

    # ============================
    # CONFIGURACIÓN DE COLUMNAS
    # ============================
    widths = [28, 18, 18, 18, 18, 18]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ============================
    # HEADER
    # ============================
    logo_path = os.path.join(
        os.getcwd(),
        "src",
        "assets",
        "logos",
        "logoFinopsLatam.png"
    )

    if os.path.exists(logo_path):
        logo = XLImage(logo_path)
        logo.width = 110
        logo.height = 110
        ws.add_image(logo, "A1")

    ws.merge_cells("C2:F2")
    ws["C2"] = "Reporte Administrativo — FinOpsLatam"
    ws["C2"].font = Font(size=16, bold=True)
    ws["C2"].alignment = Alignment(horizontal="center")

    chile_tz = pytz.timezone("America/Santiago")
    now_cl = datetime.now(chile_tz).strftime("%d/%m/%Y %H:%M CLT")

    ws.merge_cells("C3:F3")
    ws["C3"] = f"Generado el {now_cl}"
    ws["C3"].alignment = Alignment(horizontal="right")
    ws["C3"].font = Font(size=10)

    # ============================
    # KPIs
    # ============================
    start_row = 6

    ws["A5"] = "Métrica"
    ws["B5"] = "Valor"
    ws["C5"] = "Estado"
    ws["D5"] = "Porcentaje"

    for col in ["A", "B", "C", "D"]:
        ws[f"{col}5"].font = Font(bold=True)

    total = stats["total_users"]
    active = stats["active_users"]
    inactive = stats["inactive_users"]

    active_pct = round((active / total) * 100, 1) if total else 0
    inactive_pct = round((inactive / total) * 100, 1) if total else 0

    data = [
        ("Usuarios totales", total, "", ""),
        ("Usuarios activos", active, "Activo", f"{active_pct}%"),
        ("Usuarios inactivos", inactive, "Inactivo", f"{inactive_pct}%"),
    ]

    for i, row in enumerate(data, start=start_row):
        ws[f"A{i}"], ws[f"B{i}"], ws[f"C{i}"], ws[f"D{i}"] = row

    # ============================
    # PIE CHART (DEBAJO KPI)
    # ============================
    pie = PieChart()
    pie.title = "Usuarios activos vs inactivos"

    labels = Reference(ws, min_col=1, min_row=7, max_row=8)
    values = Reference(ws, min_col=2, min_row=7, max_row=8)

    pie.add_data(values, titles_from_data=False)
    pie.set_categories(labels)

    ws.add_chart(pie, "F6")

    # ============================
    # USUARIOS POR PLAN (TABLA)
    # ============================
    plan_start = 14

    ws["A13"] = "Plan"
    ws["B13"] = "Cantidad"
    ws["A13"].font = ws["B13"].font = Font(bold=True)

    for i, p in enumerate(stats["users_by_plan"], start=plan_start):
        ws[f"A{i}"] = p["plan"]
        ws[f"B{i}"] = p["count"]

    # ============================
    # BAR CHART (DEBAJO TABLA PLAN)
    # ============================
    bar = BarChart()
    bar.title = "Usuarios por plan"
    bar.y_axis.title = "Cantidad"
    bar.x_axis.title = "Plan"

    data_ref = Reference(
        ws,
        min_col=2,
        min_row=plan_start - 1,
        max_row=plan_start + len(stats["users_by_plan"]) - 1,
    )

    cats_ref = Reference(
        ws,
        min_col=1,
        min_row=plan_start,
        max_row=plan_start + len(stats["users_by_plan"]) - 1,
    )

    bar.add_data(data_ref, titles_from_data=True)
    bar.set_categories(cats_ref)

    ws.add_chart(bar, "F14")

    # ============================
    # FOOTER
    # ============================
    footer_row = plan_start + len(stats["users_by_plan"]) + 10
    ws.merge_cells(f"A{footer_row}:F{footer_row}")
    ws[f"A{footer_row}"] = (
        "© 2026 FinOpsLatam — Información confidencial. Uso exclusivo interno."
    )
    ws[f"A{footer_row}"].alignment = Alignment(horizontal="center")
    ws[f"A{footer_row}"].font = Font(size=9)

    # ============================
    # EXPORT
    # ============================
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer.read()

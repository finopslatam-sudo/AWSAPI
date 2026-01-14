from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.drawing.image import Image as XLImage
from openpyxl.chart import PieChart, BarChart, Reference
from openpyxl.utils import get_column_letter
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import tempfile


def build_admin_xlsx(stats: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte Administrativo"

    title_font = Font(size=16, bold=True)
    header_font = Font(bold=True)
    center = Alignment(horizontal="center")

    chile_time = datetime.now(ZoneInfo("America/Santiago"))

    # =====================================================
    # HEADER
    # =====================================================
    logo_path = os.path.join(
        os.getcwd(),
        "src",
        "assets",
        "logos",
        "logoFinopsLatam.png"
    )
    if os.path.exists(logo_path):
        logo = XLImage(logo_path)
        logo.width = 120
        logo.height = 120
        ws.add_image(logo, "A1")

    ws["C2"] = "Reporte Administrativo — FinOpsLatam"
    ws["C2"].font = title_font

    ws["C3"] = f"Generado el {chile_time.strftime('%d/%m/%Y %H:%M CLT')}"

    # =====================================================
    # TABLA 1 — RESUMEN USUARIOS
    # =====================================================
    ws["A6"] = "Indicador"
    ws["B6"] = "Valor"
    ws["A6"].font = header_font
    ws["B6"].font = header_font

    resumen = [
        ("Usuarios totales", stats.get("total_users", 0)),
        ("Usuarios activos", stats.get("active_users", 0)),
        ("Usuarios inactivos", stats.get("inactive_users", 0)),
    ]

    for i, (label, value) in enumerate(resumen, start=7):
        ws[f"A{i}"] = label
        ws[f"B{i}"] = value

    # =====================================================
    # GRÁFICO 1 — ESTADO USUARIOS
    # =====================================================
    total = stats.get("active_users", 0) + stats.get("inactive_users", 0)
    active_pct = round((stats.get("active_users", 0) / total) * 100, 2) if total else 0
    inactive_pct = round(100 - active_pct, 2)

    ws["D6"] = "Estado"
    ws["E6"] = "Porcentaje"
    ws["D6"].font = header_font
    ws["E6"].font = header_font

    ws.append(["Activos", active_pct])
    ws.append(["Inactivos", inactive_pct])

    pie = PieChart()
    pie.title = "Usuarios activos vs inactivos"
    labels = Reference(ws, min_col=4, min_row=7, max_row=8)
    data = Reference(ws, min_col=5, min_row=6, max_row=8)
    pie.add_data(data, titles_from_data=True)
    pie.set_categories(labels)
    ws.add_chart(pie, "D10")

    # =====================================================
    # TABLA 2 — USUARIOS POR PLAN
    # =====================================================
    start_row = 20
    ws[f"A{start_row}"] = "Plan"
    ws[f"B{start_row}"] = "Cantidad"
    ws[f"A{start_row}"].font = header_font
    ws[f"B{start_row}"].font = header_font

    for i, plan in enumerate(stats.get("users_by_plan", []), start=start_row + 1):
        ws[f"A{i}"] = plan.get("plan", "")
        ws[f"B{i}"] = plan.get("count", 0)

    # =====================================================
    # GRÁFICO 2 — USUARIOS POR PLAN
    # =====================================================
    last_row = start_row + len(stats.get("users_by_plan", []))
    bar = BarChart()
    bar.title = "Usuarios por plan"
    bar.y_axis.title = "Cantidad"
    bar.x_axis.title = "Plan"

    data = Reference(ws, min_col=2, min_row=start_row, max_row=last_row)
    cats = Reference(ws, min_col=1, min_row=start_row + 1, max_row=last_row)
    bar.add_data(data, titles_from_data=True)
    bar.set_categories(cats)

    ws.add_chart(bar, "D20")

    # =====================================================
    # FOOTER
    # =====================================================
    ws[f"A{last_row + 8}"] = (
        "© 2026 FinOpsLatam — Información confidencial. Uso exclusivo interno."
    )

    # =====================================================
    # AJUSTES
    # =====================================================
    for col in range(1, 6):
        ws.column_dimensions[get_column_letter(col)].width = 30

    # =====================================================
    # EXPORT
    # =====================================================
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    wb.save(tmp.name)

    with open(tmp.name, "rb") as f:
        return f.read()

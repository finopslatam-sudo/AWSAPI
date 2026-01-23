"""
CLIENT XLSX REPORT
==================

Genera un reporte XLSX visible para el cliente FinOpsLatam.

- Contiene únicamente métricas del cliente autenticado
- No expone información global
- Orientado a Excel / BI
"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime
from io import BytesIO
import pytz


def build_client_xlsx(stats: dict) -> bytes:
    """
    Construye el archivo Excel del cliente.
    """

    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte Cliente"

    # ============================
    # CONFIGURACIÓN DE COLUMNAS
    # ============================
    ws.column_dimensions[get_column_letter(1)].width = 30
    ws.column_dimensions[get_column_letter(2)].width = 25

    # ============================
    # HEADER
    # ============================
    chile_tz = pytz.timezone("America/Santiago")
    generated_at = datetime.now(chile_tz).strftime("%d/%m/%Y %H:%M CLT")

    ws.merge_cells("A1:B1")
    ws["A1"] = "Reporte de Cliente — FinOpsLatam"
    ws["A1"].font = Font(size=16, bold=True)
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A2:B2")
    ws["A2"] = f"Generado el {generated_at}"
    ws["A2"].font = Font(size=10)
    ws["A2"].alignment = Alignment(horizontal="center")

    # ============================
    # MÉTRICAS
    # ============================
    table_start = 4

    ws[f"A{table_start}"] = "Métrica"
    ws[f"B{table_start}"] = "Valor"
    ws[f"A{table_start}"].font = ws[f"B{table_start}"].font = Font(bold=True)

    plan = stats.get("plan") or "Sin plan activo"

    rows = [
        ("Plan contratado", plan),
        ("Usuarios asociados", stats["user_count"]),
        ("Servicios activos", stats["active_services"]),
    ]

    for i, (metric, value) in enumerate(rows, start=table_start + 1):
        ws[f"A{i}"] = metric
        ws[f"B{i}"] = value

    # ============================
    # FOOTER
    # ============================
    footer_row = table_start + len(rows) + 3
    ws.merge_cells(f"A{footer_row}:B{footer_row}")
    ws[f"A{footer_row}"] = (
        "© 2026 FinOpsLatam — Información confidencial."
    )
    ws[f"A{footer_row}"].font = Font(size=9)
    ws[f"A{footer_row}"].alignment = Alignment(horizontal="center")

    # ============================
    # EXPORT
    # ============================
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer.read()

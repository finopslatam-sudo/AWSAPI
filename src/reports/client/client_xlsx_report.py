"""
CLIENT XLSX REPORT
==================

Genera un reporte XLSX visible para el cliente FinOpsLatam.

- Contiene únicamente métricas del cliente autenticado
- No expone información global
- Orientado a Excel / BI
"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
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
    ws.title = "Resumen"

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
    ws["A1"] = "Reporte - FinOpsLatam"
    ws["A1"].font = Font(size=16, bold=True, color="0f172a")
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A2:B2")
    ws["A2"] = f"Generado el {generated_at}"
    ws["A2"].font = Font(size=10, color="475569")
    ws["A2"].alignment = Alignment(horizontal="center")

    # ============================
    # MÉTRICAS
    # ============================
    table_start = 4

    header_fill = PatternFill("solid", fgColor="0f172a")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Border(left=Side(style="thin", color="e2e8f0"),
                  right=Side(style="thin", color="e2e8f0"),
                  top=Side(style="thin", color="e2e8f0"),
                  bottom=Side(style="thin", color="e2e8f0"))

    ws[f"A{table_start}"] = "Métrica"
    ws[f"B{table_start}"] = "Valor"
    for cell in (ws[f"A{table_start}"], ws[f"B{table_start}"]):
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin

    plan = stats.get("plan") or "Sin plan activo"

    rows = [
        ("Plan contratado", plan),
        ("Usuarios asociados", stats["user_count"]),
        ("Servicios activos", stats["active_services"]),
        ("Findings activos", stats.get("findings_summary", {}).get("active", 0)),
        ("Findings resueltos", stats.get("findings_summary", {}).get("resolved", 0)),
        ("Findings high", stats.get("findings_summary", {}).get("high", 0)),
        ("Ahorro mensual estimado", stats.get("findings_summary", {}).get("savings", 0)),
    ]

    for i, (metric, value) in enumerate(rows, start=table_start + 1):
        ws[f"A{i}"] = metric
        ws[f"A{i}"].border = thin
        ws[f"B{i}"] = value
        ws[f"B{i}"].border = thin

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
    # SHEET DE FINDINGS
    # ============================
    findings = stats.get("findings") or []
    ws2 = wb.create_sheet(title="Findings")
    columns = ["Cuenta", "Servicio", "Severidad", "Recurso", "Ahorro mensual", "Detectado"]
    widths = [25, 18, 12, 40, 18, 22]
    for idx, width in enumerate(widths, start=1):
        ws2.column_dimensions[get_column_letter(idx)].width = width

    for col, name in enumerate(columns, start=1):
        cell = ws2.cell(row=1, column=col, value=name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin

    for r, f in enumerate(findings, start=2):
        ws2.cell(row=r, column=1, value=f.get("aws_account_name") or f.get("aws_account_number") or "").border = thin
        ws2.cell(row=r, column=2, value=f.get("aws_service", "")).border = thin
        ws2.cell(row=r, column=3, value=f.get("severity", "")).border = thin
        ws2.cell(row=r, column=4, value=f.get("resource_id", "")).border = thin
        ws2.cell(row=r, column=5, value=float(f.get("estimated_monthly_savings") or 0)).border = thin
        ws2.cell(row=r, column=6, value=f.get("created_at", "")[:19]).border = thin

    # ============================
    # EXPORT
    # ============================
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer.read()

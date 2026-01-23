"""
XLSX EXPORTER BASE
=================

Utilidad base para generar archivos Excel (.xlsx).
Usado por reportes administrativos y de clientes.

Este módulo NO contiene lógica de negocio.
"""

from openpyxl import Workbook
from io import BytesIO


def build_xlsx(sheet_name: str, headers: list, rows: list) -> bytes:
    """
    Construye un archivo XLSX simple y reutilizable.

    :param sheet_name: Nombre de la hoja
    :param headers: Lista de encabezados
    :param rows: Lista de filas (listas o tuplas)
    :return: Archivo XLSX en bytes
    """
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name

    # Header
    ws.append(headers)

    # Rows
    for row in rows:
        ws.append(row)

    # Export
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer.read()

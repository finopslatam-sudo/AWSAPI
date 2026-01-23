"""
CSV EXPORTER BASE
=================

Utilidad base para construir archivos CSV en UTF-8.
Usado por reportes admin y cliente.

Este módulo NO contiene lógica de negocio.
"""

import csv
from io import StringIO


def build_csv(headers: list, rows: list) -> bytes:
    """
    Construye un CSV estándar en UTF-8.

    :param headers: Lista de nombres de columnas
    :param rows: Lista de filas (listas o tuplas)
    :return: CSV en bytes (UTF-8)
    """
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    return output.getvalue().encode("utf-8")

"""
PDF EXPORTER BASE
================

Utilidad base para generar PDFs usando ReportLab.
Usado por reportes administrativos y de clientes.

Este módulo NO contiene lógica de negocio.
"""

from io import BytesIO
from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm


def build_pdf(elements) -> bytes:
    """
    Construye un PDF en formato A4.

    :param elements: Lista de elementos ReportLab (Paragraph, Table, Image, etc.)
    :return: PDF en bytes
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    doc.build(elements)
    buffer.seek(0)

    return buffer.getvalue()

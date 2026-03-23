"""Pie del PDF ejecutivo."""

from reportlab.platypus import Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle

from .styles import MUTED, BORDER


def build_footer(styles) -> list:
    return [
        Spacer(1, 14),
        HRFlowable(width="100%", thickness=0.4, color=BORDER),
        Paragraph(
            "FinOpsLatam — Plataforma de Optimización Financiera para AWS  ·  "
            "contacto@finopslatam.com  ·  Confidencial",
            ParagraphStyle("footer", fontSize=7, textColor=MUTED, alignment=1, leading=10),
        ),
    ]

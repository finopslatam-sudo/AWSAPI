"""Header e información general del PDF ejecutivo."""

import os
from datetime import datetime

from reportlab.platypus import Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle

from .styles import ACCENT, DARK, MUTED, BG_ALT, BORDER


def build_header(styles, usable_w: float) -> list:
    logo_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "assets", "logos", "logoFinopsLatam.png"
    )
    logo = Image(logo_path, width=100, height=33) if os.path.exists(logo_path) else Spacer(100, 33)

    header_data = [[
        logo,
        Table(
            [
                [Paragraph(
                    "Resumen Ejecutivo FinOps",
                    ParagraphStyle("ht", fontSize=16, fontName="Helvetica-Bold", textColor=DARK),
                )],
                [Paragraph(
                    f"Generado: {datetime.utcnow().strftime('%d de %B de %Y — %H:%M UTC')}",
                    ParagraphStyle("hd", fontSize=8, textColor=MUTED),
                )],
            ],
            colWidths=[usable_w - 120],
        ),
    ]]
    header_tbl = Table(header_data, colWidths=[120, usable_w - 120])
    header_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [
        header_tbl,
        HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10, spaceBefore=6),
    ]


def build_info_row(styles, plan: str, accounts: int, account_label: str, users: int) -> list:
    info_data = [[
        Paragraph("<b>Plan</b>",        styles["td"]), Paragraph(plan, styles["td"]),
        Paragraph("<b>Cuentas AWS</b>", styles["td"]), Paragraph(f"{accounts}  ({account_label})", styles["td"]),
        Paragraph("<b>Usuarios</b>",    styles["td"]), Paragraph(str(users), styles["td"]),
    ]]
    info_col_w = [70, 100, 90, 120, 55, 30]
    info_tbl = Table(info_data, colWidths=info_col_w)
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BG_ALT),
        ("BOX",           (0, 0), (-1, -1), 0.4, BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    return [info_tbl]

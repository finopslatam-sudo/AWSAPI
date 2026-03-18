"""
CLIENT PDF REPORT
=================

Genera el reporte PDF visible para un cliente FinOpsLatam.

- No contiene métricas globales
- No expone datos de otros clientes
- Consume datos del client_stats_provider
"""

import os
from datetime import datetime
from reportlab.platypus import Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from src.reports.exporters.pdf_base import build_pdf

PALETTE = {
    "ink": colors.HexColor("#0f172a"),
    "muted": colors.HexColor("#475569"),
    "border": colors.HexColor("#e2e8f0"),
    "bg": colors.HexColor("#f8fafc"),
    "card_rose": colors.HexColor("#fecdd3"),
    "card_green": colors.HexColor("#bbf7d0"),
    "card_amber": colors.HexColor("#fde68a"),
    "card_blue": colors.HexColor("#bfdbfe"),
}


def build_client_pdf(stats: dict) -> bytes:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CardTitle", fontSize=11, textColor=PALETTE["muted"], leading=14))
    styles.add(ParagraphStyle(name="CardValue", fontSize=18, textColor=PALETTE["ink"], leading=20))
    styles.add(ParagraphStyle(name="TableHeader", fontSize=9, textColor=colors.white, leading=11))
    styles.add(ParagraphStyle(name="TableCell", fontSize=8, textColor=PALETTE["ink"], leading=10))

    elements = []

    logo_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "assets",
        "logos",
        "logoFinopsLatam.png"
    )
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=120, height=40))
        elements.append(Spacer(1, 6))

    elements.append(Paragraph("Reporte de Cliente – FinOpsLatam", styles["Title"]))
    elements.append(Spacer(1, 12))

    elements.append(
        Paragraph(
            f"Generado: {datetime.utcnow().strftime('%d-%m-%Y %H:%M UTC')}",
            styles["Normal"]
        )
    )
    elements.append(Spacer(1, 20))

    plan = stats.get("plan") or "Sin plan activo"
    summary = stats.get("findings_summary") or {}
    cards = [
        ("Active", int(summary.get("active", 0)), "#fef2f2", "#ef4444"),
        ("Resolved", int(summary.get("resolved", 0)), "#ecfdf3", "#22c55e"),
        ("High Severity", int(summary.get("high", 0)), "#fff7ed", "#f97316"),
        ("Monthly Savings", f"${float(summary.get('savings', 0)):.0f}", "#eff6ff", "#2563eb"),
    ]

    # Datos generales
    gen_data = [
        ["Plan", plan],
        ["Usuarios", str(stats.get("user_count", 0))],
    ]
    gen_table = Table(gen_data, colWidths=[140, 260])
    gen_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALETTE["bg"]),
        ("TEXTCOLOR", (0, 0), (-1, -1), PALETTE["ink"]),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, PALETTE["border"]),
        ("BOX", (0, 0), (-1, -1), 0.3, PALETTE["border"]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(gen_table)
    elements.append(Spacer(1, 14))

    # Cards de métricas
    card_cells = []
    for title, value, bg, fg in cards:
        inner = Table(
            [
                [Paragraph(f"<b>{title}</b>", styles["CardTitle"])],
                [Paragraph(str(value), ParagraphStyle(name="cardValueInline", textColor=colors.HexColor(fg), fontSize=18))],
            ],
            colWidths=[130],
        )
        inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(bg)),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        card_cells.append([inner])

    cards_table = Table([card_cells[:2], card_cells[2:]], colWidths=[150, 150], hAlign="LEFT")
    cards_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(cards_table)
    elements.append(Spacer(1, 18))

    # Tabla de findings
    findings = stats.get("findings", []) or []
    if findings:
        headers = ["Cuenta", "Servicio", "Severidad", "Recurso", "Ahorro mensual", "Detectado"]
        data = [headers]
        for f in findings:
            data.append([
                f.get("aws_account_name") or f.get("aws_account_number") or "",
                f.get("aws_service", ""),
                f.get("severity", ""),
                f.get("resource_id", ""),
                f"${float(f.get('estimated_monthly_savings') or 0):.0f}",
                f.get("created_at", "")[:10],
            ])

        table = Table(data, repeatRows=1, colWidths=[90, 70, 60, 120, 80, 80])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PALETTE["ink"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, 0), "LEFT"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("BACKGROUND", (0, 1), (-1, -1), PALETTE["bg"]),
            ("TEXTCOLOR", (0, 1), (-1, -1), PALETTE["ink"]),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, PALETTE["border"]),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PALETTE["bg"], colors.white]),
        ]))
        elements.append(Paragraph("Findings", styles["Heading2"]))
        elements.append(Spacer(1, 8))
        elements.append(table)

    return build_pdf(elements)

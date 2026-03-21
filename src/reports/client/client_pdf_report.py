"""
CLIENT PDF REPORT
=================
Genera el reporte PDF visible para un cliente FinOpsLatam.
Orientacion: A4 Landscape para acomodar todas las columnas sin superposicion.
"""

import os
from io import BytesIO
from datetime import datetime

from reportlab.platypus import Paragraph, Spacer, Image, Table, TableStyle, SimpleDocTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors

# =====================================================
#   PALETTE
# =====================================================
INK    = colors.HexColor("#0f172a")
MUTED  = colors.HexColor("#475569")
BORDER = colors.HexColor("#cbd5e1")
BG     = colors.HexColor("#f8fafc")
WHITE  = colors.white
HEADER = colors.HexColor("#1e293b")

# =====================================================
#   HOW-TO-FIX MAP
# =====================================================
RESOLUTION = {
    "EBS_GP2_TO_GP3":                  "Migrar volumen de GP2 a GP3 via modify-volume. Sin downtime.",
    "EC2_UNDERUTILIZED":               "Rightsizing: reducir tipo de instancia o apagarla si no esta en uso.",
    "STOPPED_INSTANCE":                "Crear AMI de respaldo y terminar la instancia para detener el cobro.",
    "UNATTACHED_VOLUME":               "Tomar snapshot y eliminar el volumen desconectado.",
    "CLOUDWATCH_NO_RETENTION":         "Configurar politica de retencion en el Log Group (ej. 30-90 dias).",
    "CLOUDWATCH_HIGH_RETENTION":       "Reducir retencion del Log Group o mover logs frios a S3 Glacier.",
    "CLOUDWATCH_STORAGE_RIGHTSIZING":  "Reducir retencion o filtrar metricas enviadas a CloudWatch.",
    "LAMBDA_HIGH_MEMORY":              "Reducir memoria de la funcion Lambda con AWS Lambda Power Tuning.",
    "LAMBDA_MEMORY_RIGHTSIZING":       "Ajustar memoria de Lambda al valor optimo con Power Tuning.",
    "LAMBDA_DEPRECATED_RUNTIME":       "Actualizar el runtime de Lambda a una version soportada.",
    "RDS_UNDERUTILIZED":               "Escalar hacia abajo la instancia RDS o usar Aurora Serverless.",
    "RDS_GP2_STORAGE":                 "Migrar almacenamiento RDS de GP2 a GP3 para reducir costo.",
    "RDS_MULTI_AZ_DISABLED":           "Habilitar Multi-AZ para alta disponibilidad (solo produccion).",
    "RDS_NOT_ENCRYPTED":               "Restaurar desde snapshot con cifrado habilitado.",
    "RDS_NO_BACKUP_RETENTION":         "Configurar retencion de backups automaticos a minimo 7 dias.",
    "RDS_PUBLIC_ACCESS":               "Desactivar acceso publico y usar VPC o bastion host.",
    "DYNAMODB_EMPTY_TABLE":            "Exportar a S3 si hay datos y eliminar la tabla vacia.",
    "DYNAMODB_PROVISIONED_MODE":       "Cambiar a On-Demand o ajustar las unidades de capacidad.",
    "DYNAMODB_PROVISIONED_RIGHTSIZING":"Ajustar Read/Write Capacity Units al consumo real.",
    "NAT_IDLE_GATEWAY":                "Eliminar NAT Gateway sin trafico (verificar rutas antes).",
    "S3_STORAGE_RIGHTSIZING_REVIEW":   "Aplicar Intelligent-Tiering o ciclo de vida para objetos frios.",
    "EC2_RI":                          "Adquirir Reserved Instances de 1 anio para uso sostenido (-40%).",
    "RI_UNUSED":                       "Vender RIs no usadas en AWS Marketplace o reasignarlas.",
    "LOW_RI_COVERAGE":                 "Aumentar cobertura de Reserved Instances en instancias de uso alto.",
    "SP_REVIEW":                       "Evaluar Savings Plans para workloads con uso predecible.",
    "ECS_SERVICE_RIGHTSIZING_REVIEW":  "Revisar limites de CPU/memoria en tareas ECS.",
    "EKS_NODEGROUP_RIGHTSIZING_REVIEW":"Ajustar tipo de instancia y tamanio del Node Group de EKS.",
    "REDSHIFT_UNDERUTILIZED":          "Pausar el cluster o migrar a Redshift Serverless.",
    "RIGHTSIZING_OPPORTUNITY":         "Migrar a tipo/tamanio inferior que cubra la carga real.",
}

def _resolution(finding_type: str) -> str:
    return RESOLUTION.get(
        finding_type,
        "Revisar el recurso en la consola AWS y evaluar optimizacion."
    )


# =====================================================
#   BUILD PDF
# =====================================================
def build_client_pdf(stats: dict) -> bytes:

    buffer = BytesIO()

    # Landscape A4: 841 x 595 pt
    page = landscape(A4)
    margin = 1.8 * cm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    # Ancho util aprox: 841 - 2*51 = 739 pt
    usable_w = page[0] - 2 * margin

    # =====================================================
    #   STYLES
    # =====================================================
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TH",
        fontSize=8, textColor=WHITE, leading=10, spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        name="TD",
        fontSize=7.5, textColor=INK, leading=10, spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        name="TDSmall",
        fontSize=7, textColor=MUTED, leading=9, spaceAfter=0,
    ))

    elements = []

    # =====================================================
    #   LOGO
    # =====================================================
    logo_path = os.path.join(
        os.path.dirname(__file__), "..", "assets", "logos", "logoFinopsLatam.png"
    )
    if os.path.exists(logo_path):
        elements.append(Image(logo_path, width=110, height=36))
        elements.append(Spacer(1, 4))

    # =====================================================
    #   TITULO
    # =====================================================
    elements.append(Paragraph("Reporte de Cliente – FinOpsLatam", styles["Title"]))
    elements.append(Paragraph(
        f"Generado: {datetime.utcnow().strftime('%d-%m-%Y %H:%M UTC')}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 14))

    # =====================================================
    #   TABLA INFO GENERAL (izquierda, con Cuentas)
    # =====================================================
    plan          = stats.get("plan") or "Sin plan activo"
    user_count    = stats.get("user_count", 0)
    account_count = stats.get("account_count", 0)

    gen_data = [
        ["Plan",     plan],
        ["Cuentas",  str(account_count)],
        ["Usuarios", str(user_count)],
    ]
    gen_table = Table(gen_data, colWidths=[100, 220], hAlign="LEFT")
    gen_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BG),
        ("TEXTCOLOR",     (0, 0), (-1, -1), INK),
        ("FONTNAME",      (0, 0), (0, -1),  "Helvetica-Bold"),
        ("FONTNAME",      (1, 0), (1, -1),  "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, BORDER),
        ("BOX",           (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    elements.append(gen_table)
    elements.append(Spacer(1, 14))

    # =====================================================
    #   CARDS DE METRICAS (4 cards en fila)
    # =====================================================
    summary = stats.get("findings_summary") or {}
    cards_def = [
        ("Active",          str(int(summary.get("active", 0))),   "#fef2f2", "#ef4444"),
        ("Resolved",        str(int(summary.get("resolved", 0))), "#ecfdf5", "#22c55e"),
        ("High Severity",   str(int(summary.get("high", 0))),     "#fff7ed", "#f97316"),
        ("Monthly Savings", f"USD ${float(summary.get('savings', summary.get('estimated_monthly_savings', 0))):.0f}",
                                                                   "#eff6ff", "#2563eb"),
    ]

    card_w = usable_w / 4 - 6
    card_cells = []
    for title, value, bg, fg in cards_def:
        inner = Table(
            [
                [Paragraph(f"<b>{title}</b>",
                           ParagraphStyle("ct", fontSize=8, textColor=MUTED, leading=10))],
                [Paragraph(value,
                           ParagraphStyle("cv", fontSize=16, textColor=colors.HexColor(fg), leading=18))],
            ],
            colWidths=[card_w],
        )
        inner.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor(bg)),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        card_cells.append(inner)

    cards_row = Table([card_cells], colWidths=[card_w + 6] * 4, hAlign="LEFT")
    cards_row.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(cards_row)
    elements.append(Spacer(1, 18))

    # =====================================================
    #   TABLA DE FINDINGS & RIGHTSIZING
    # =====================================================
    findings = stats.get("findings", []) or []
    if findings:
        elements.append(Paragraph("Findings & Rightsizing", styles["Heading2"]))
        elements.append(Spacer(1, 6))

        # Anchos de columna (total = usable_w ~739 pt)
        # Cuenta  Servicio  Recurso  Region  Ahorro  Finding  How to Fix
        col_w = [90, 60, 100, 62, 52, 155, 160]
        # Ajustar si hay diferencia residual
        diff = usable_w - sum(col_w)
        col_w[-1] += diff   # absorber en la ultima columna

        headers = ["Cuenta", "Servicio", "Recurso", "Region",
                   "Ahorro", "Finding", "How to Fix"]

        th_style = styles["TH"]
        td_style = styles["TD"]
        td_small = styles["TDSmall"]

        data = [[Paragraph(h, th_style) for h in headers]]

        for f in findings:
            account  = f.get("aws_account_name") or f.get("aws_account_number") or ""
            service  = f.get("aws_service", "")
            resource = f.get("resource_id", "")
            region   = f.get("region", "") or ""
            savings  = f"USD ${float(f.get('estimated_monthly_savings') or 0):.0f}"
            finding  = f.get("message", "") or ""
            how_fix  = _resolution(f.get("finding_type", ""))

            data.append([
                Paragraph(account,  td_style),
                Paragraph(service,  td_style),
                Paragraph(resource, td_small),
                Paragraph(region,   td_style),
                Paragraph(savings,  td_style),
                Paragraph(finding,  td_small),
                Paragraph(how_fix,  td_small),
            ])

        table = Table(data, colWidths=col_w, repeatRows=1, splitByRow=True)
        table.setStyle(TableStyle([
            # Header
            ("BACKGROUND",    (0, 0), (-1, 0),  HEADER),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("TOPPADDING",    (0, 0), (-1, 0),  6),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  6),
            ("LEFTPADDING",   (0, 0), (-1, 0),  6),
            # Filas
            ("BACKGROUND",    (0, 1), (-1, -1), WHITE),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BG]),
            ("TEXTCOLOR",     (0, 1), (-1, -1), INK),
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("TOPPADDING",    (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("LEFTPADDING",   (0, 1), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            # Bordes
            ("GRID",          (0, 0), (-1, -1), 0.25, BORDER),
            # Alineacion
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("ALIGN",         (4, 0), (4, -1),  "RIGHT"),   # Ahorro derecha
        ]))
        elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

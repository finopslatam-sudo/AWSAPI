"""
CLIENT XLSX REPORT
==================
Genera un reporte XLSX visible para el cliente FinOpsLatam.
"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from io import BytesIO
import pytz


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


def _thin_border():
    s = Side(style="thin", color="CBD5E1")
    return Border(left=s, right=s, top=s, bottom=s)


def build_client_xlsx(stats: dict) -> bytes:

    wb = Workbook()

    # ================================================
    # HOJA 1 — RESUMEN
    # ================================================
    ws = wb.active
    ws.title = "Resumen"

    chile_tz = pytz.timezone("America/Santiago")
    generated_at = datetime.now(chile_tz).strftime("%d/%m/%Y %H:%M CLT")

    thin        = _thin_border()
    hdr_fill    = PatternFill("solid", fgColor="1E293B")
    hdr_font    = Font(color="FFFFFF", bold=True, size=10)
    label_font  = Font(bold=True, color="0F172A", size=10)
    value_font  = Font(color="334155", size=10)
    title_font  = Font(bold=True, size=15, color="0F172A")
    sub_font    = Font(size=9, color="64748B")

    # Ancho de columnas del resumen
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 28

    # Título
    ws.merge_cells("A1:B1")
    ws["A1"] = "Reporte FinOpsLatam — Findings & Rightsizing"
    ws["A1"].font = title_font
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 24

    ws.merge_cells("A2:B2")
    ws["A2"] = f"Generado el {generated_at}"
    ws["A2"].font = sub_font
    ws["A2"].alignment = Alignment(horizontal="left")

    # Encabezado tabla resumen
    ws["A4"] = "Métrica"
    ws["B4"] = "Valor"
    for cell in (ws["A4"], ws["B4"]):
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="left", vertical="center")
        cell.border = thin

    summary = stats.get("findings_summary") or {}
    savings_val = summary.get("estimated_monthly_savings") or summary.get("savings") or 0

    summary_rows = [
        ("Plan contratado",           stats.get("plan") or "Sin plan activo"),
        ("Cuentas AWS escaneadas",    stats.get("account_count", 0)),
        ("Usuarios asociados",        stats.get("user_count", 0)),
        ("Findings activos",          summary.get("active", 0)),
        ("Findings resueltos",        summary.get("resolved", 0)),
        ("Findings severidad HIGH",   summary.get("high", 0)),
        ("Ahorro mensual estimado",   f"USD ${float(savings_val):.2f}"),
    ]

    for i, (metric, value) in enumerate(summary_rows, start=5):
        ws[f"A{i}"] = metric
        ws[f"A{i}"].font = label_font
        ws[f"A{i}"].border = thin
        ws[f"A{i}"].alignment = Alignment(vertical="center")

        ws[f"B{i}"] = value
        ws[f"B{i}"].font = value_font
        ws[f"B{i}"].border = thin
        ws[f"B{i}"].alignment = Alignment(vertical="center")

    footer_row = 5 + len(summary_rows) + 2
    ws.merge_cells(f"A{footer_row}:B{footer_row}")
    ws[f"A{footer_row}"] = "© 2026 FinOpsLatam — Información confidencial."
    ws[f"A{footer_row}"].font = Font(size=8, color="94A3B8")
    ws[f"A{footer_row}"].alignment = Alignment(horizontal="left")

    # ================================================
    # HOJA 2 — FINDINGS & RIGHTSIZING (completa)
    # ================================================
    ws2 = wb.create_sheet(title="Findings & Rightsizing")

    columns = [
        ("Account",        28),
        ("Service",        16),
        ("Type",           28),
        ("Resource",       38),
        ("Region",         14),
        ("Savings (USD)",  16),
        ("Status",         12),
        ("Severity",       12),
        ("Finding",        50),
        ("How to Fix",     55),
        ("Detected At",    18),
    ]

    for idx, (name, width) in enumerate(columns, start=1):
        ws2.column_dimensions[get_column_letter(idx)].width = width
        cell = ws2.cell(row=1, column=idx, value=name)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)
        cell.border = thin

    ws2.row_dimensions[1].height = 18

    findings = stats.get("findings") or []
    alt_fill = PatternFill("solid", fgColor="F8FAFC")

    for r, f in enumerate(findings, start=2):
        savings = float(f.get("estimated_monthly_savings") or 0)
        detected = (f.get("created_at") or f.get("detected_at") or "")[:10]
        row_fill = alt_fill if r % 2 == 0 else None

        row_data = [
            f.get("aws_account_name") or f.get("aws_account_number") or "",
            f.get("aws_service", ""),
            f.get("finding_type", ""),
            f.get("resource_id", ""),
            f.get("region", "") or "",
            f"${savings:.2f}",
            "Resolved" if f.get("resolved") else "Active",
            f.get("severity", ""),
            f.get("message", "") or "",
            _resolution(f.get("finding_type", "")),
            detected,
        ]

        for col, value in enumerate(row_data, start=1):
            cell = ws2.cell(row=r, column=col, value=value)
            cell.font = value_font
            cell.border = thin
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=(col in (9, 10)),   # wrap solo en Finding y How to Fix
            )
            if row_fill:
                cell.fill = row_fill

        ws2.row_dimensions[r].height = 30

    # Freeze header row
    ws2.freeze_panes = "A2"

    # ================================================
    # EXPORT
    # ================================================
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()

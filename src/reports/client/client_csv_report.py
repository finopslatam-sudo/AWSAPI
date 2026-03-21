"""
CLIENT CSV REPORT
=================

Exporta métricas del cliente en formato CSV,
orientado a Excel y herramientas BI.
"""

from src.reports.exporters.csv_base import build_csv

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


def build_client_csv(stats: dict) -> bytes:
    findings = stats.get("findings") or []

    headers = [
        "Account",
        "Service",
        "Type",
        "Resource",
        "Region",
        "Savings (USD)",
        "Status",
        "Severity",
        "Finding",
        "How to Fix",
        "Detected At",
    ]

    detail_rows = []
    for f in findings:
        savings = f.get("estimated_monthly_savings", 0) or 0
        detected = (f.get("created_at") or f.get("detected_at") or "")[:10]

        detail_rows.append([
            f.get("aws_account_name") or f.get("aws_account_number") or "",
            f.get("aws_service", ""),
            f.get("finding_type", ""),
            f.get("resource_id", ""),
            f.get("region", "") or "",
            f"${float(savings):.2f}",
            "Resolved" if f.get("resolved") else "Active",
            f.get("severity", ""),
            f.get("message", "") or "",
            _resolution(f.get("finding_type", "")),
            detected,
        ])

    return build_csv(headers, detail_rows)

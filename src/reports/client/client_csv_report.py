"""
CLIENT CSV REPORT
=================

Exporta métricas del cliente en formato CSV,
orientado a Excel y herramientas BI.
"""

from src.reports.exporters.csv_base import build_csv


def build_client_csv(stats: dict) -> bytes:
    findings = stats.get("findings") or []
    headers = ["service", "account", "type", "resource", "region", "savings", "status", "action"]

    detail_rows = []
    for f in findings:
        detail_rows.append([
            f.get("aws_service", ""),
            f.get("aws_account_name") or f.get("aws_account_number") or "",
            f.get("finding_type", ""),
            f.get("resource_id", ""),
            f.get("region", ""),
            f.get("estimated_monthly_savings", 0),
            "Resolved" if f.get("resolved") else "Active",
            f.get("message", "") or "",
        ])

    return build_csv(headers, detail_rows)

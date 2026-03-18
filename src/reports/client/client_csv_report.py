"""
CLIENT CSV REPORT
=================

Exporta métricas del cliente en formato CSV,
orientado a Excel y herramientas BI.
"""

from src.reports.exporters.csv_base import build_csv


def build_client_csv(stats: dict) -> bytes:
    findings_summary = stats.get("findings_summary") or {}
    findings = stats.get("findings") or []

    headers = ["Reporte - FinopsLatam", "metric", "value", "account", "service", "severity", "resource", "monthly_savings", "detected_at"]

    rows = []
    rows.append(["summary", "plan", stats.get("plan") or "Sin plan activo", "", "", "", "", "", ""])
    rows.append(["summary", "user_count", stats.get("user_count", 0), "", "", "", "", "", ""])
    rows.append(["summary", "active_services", stats.get("active_services", 0), "", "", "", "", "", ""])
    rows.append(["summary", "findings_active", findings_summary.get("active", 0), "", "", "", "", "", ""])
    rows.append(["summary", "findings_resolved", findings_summary.get("resolved", 0), "", "", "", "", "", ""])
    rows.append(["summary", "findings_high", findings_summary.get("high", 0), "", "", "", "", "", ""])
    rows.append(["summary", "monthly_savings", findings_summary.get("savings", 0), "", "", "", "", "", ""])

    # Findings detail
    for f in findings:
        rows.append([
            "finding",
            f.get("severity", ""),
            f.get("message", "") or "",
            f.get("aws_account_name") or f.get("aws_account_number") or "",
            f.get("aws_service", ""),
            f.get("severity", ""),
            f.get("resource_id", ""),
            f.get("estimated_monthly_savings", 0),
            f.get("created_at", "")[:19],
        ])

    return build_csv(headers, rows)

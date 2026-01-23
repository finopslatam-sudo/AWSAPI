"""
CLIENT CSV REPORT
=================

Exporta métricas del cliente en formato CSV,
orientado a Excel y herramientas BI.
"""

from src.reports.exporters.csv_base import build_csv


def build_client_csv(stats: dict) -> bytes:
    headers = ["metric", "value"]

    rows = [
        ["user_count", stats["user_count"]],
        ["active_services", stats["active_services"]],
        ["plan", stats.get("plan") or "Sin plan activo"],
    ]

    return build_csv(headers, rows)
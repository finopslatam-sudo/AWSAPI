"""
INVENTORY CSV REPORT
====================
Exporta el inventario completo de recursos AWS en formato CSV.
Incluye: cuenta, servicio, tipo, recurso, región, estado,
         hallazgos activos, severidad máxima y ahorro estimado.
"""

from src.reports.exporters.csv_base import build_csv


def build_inventory_csv(stats: dict) -> bytes:

    resources = stats.get("resources") or []

    headers = [
        "Cuenta AWS",
        "Servicio",
        "Tipo de Recurso",
        "ID de Recurso",
        "Región",
        "Estado",
        "Con Hallazgos",
        "Nº Hallazgos",
        "Severidad Máxima",
        "Ahorro Estimado (USD/mes)",
        "Tags",
        "Detectado el",
        "Última vez visto",
    ]

    rows = []
    for r in resources:
        rows.append([
            r.get("account_name", ""),
            r.get("service_name", ""),
            r.get("resource_type", ""),
            r.get("resource_id", ""),
            r.get("region", ""),
            r.get("state", ""),
            "Sí" if r.get("has_findings") else "No",
            r.get("findings_count", 0),
            r.get("max_severity", "—"),
            f"${r.get('est_savings', 0):.2f}",
            r.get("tags", "—"),
            r.get("detected_at", "—"),
            r.get("last_seen_at", "—"),
        ])

    return build_csv(headers, rows)

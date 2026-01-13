from reports.exporters.csv_base import build_csv

def build_client_csv(stats: dict) -> bytes:
    """
    CSV orientado a Excel / BI del CLIENTE.
    """

    headers = ["metric", "value"]

    rows = [
        ["user_count", stats["user_count"]],
        ["active_services", stats["active_services"]],
        ["plan", stats["plan"]],
    ]

    return build_csv(headers, rows)

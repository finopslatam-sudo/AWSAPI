from src.reports.exporters.csv_base import build_csv

def build_admin_csv(stats: dict) -> bytes:
    """
    CSV orientado a BI / Excel.
    """

    headers = [
        "metric",
        "value"
    ]

    rows = [
        ["total_users", stats["total_users"]],
        ["active_users", stats["active_users"]],
        ["inactive_users", stats["inactive_users"]],
    ]

    for item in stats["users_by_plan"]:
        rows.append([
            f"users_plan_{item['plan']}",
            item["count"]
        ])

    return build_csv(headers, rows)

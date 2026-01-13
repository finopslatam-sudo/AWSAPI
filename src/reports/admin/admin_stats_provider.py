def get_admin_stats():
    """
    Fuente única de datos administrativos.
    Este método puede ser reutilizado por:
    - PDF
    - CSV
    - Dashboards
    - API
    """

    # ⚠️ Usa aquí tus queries reales
    total_users = get_total_users()
    active_users = get_active_users()
    inactive_users = get_inactive_users()

    users_by_plan = get_users_grouped_by_plan()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "users_by_plan": users_by_plan,
    }

from src.services.admin_stats_service import (
    get_total_users,
    get_active_users,
    get_inactive_users,
    get_users_grouped_by_plan,
)


def get_admin_stats():
    return {
        "total_users": get_total_users(),
        "active_users": get_active_users(),
        "inactive_users": get_inactive_users(),
        "users_by_plan": get_users_grouped_by_plan(),
    }
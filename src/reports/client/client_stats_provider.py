def get_client_stats(client_id: int):
    """
    Datos visibles SOLO para el cliente.
    Nunca incluir métricas globales.
    """

    # ⚠️ Ajusta a tus modelos reales
    user_count = get_users_by_client(client_id)
    active_services = get_active_services_by_client(client_id)
    current_plan = get_client_plan(client_id)

    return {
        "client_id": client_id,
        "user_count": user_count,
        "active_services": active_services,
        "plan": current_plan,
    }
from services.client_stats_service import (
    get_users_by_client,
    get_active_services_by_client,
    get_client_plan,
)


def get_client_stats(client_id: int):
    return {
        "client_id": client_id,
        "user_count": get_users_by_client(client_id),
        "active_services": get_active_services_by_client(client_id),
        "plan": get_client_plan(client_id),
    }

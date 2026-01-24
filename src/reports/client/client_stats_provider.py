"""
CLIENT STATS PROVIDER
=====================

Provee métricas visibles únicamente para un cliente.

IMPORTANTE:
- Nunca expone métricas globales
- Nunca incluye datos de otros clientes
- No maneja autenticación (eso vive en routes)
"""

from src.services.client_stats_service import (
    get_users_by_client,
    get_active_services_by_client,
    get_client_plan,
)


def get_client_stats(client_id: int) -> dict:
    """
    Datos visibles SOLO para el cliente.
    Nunca incluir métricas globales.
    """

    return {
        "client_id": client_id,
        "user_count": get_users_by_client(client_id),
        "active_services": get_active_services_by_client(client_id),
        "plan": get_client_plan(client_id),
    }

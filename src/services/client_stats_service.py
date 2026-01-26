"""
CLIENT STATS SERVICE
====================

Servicios de estadísticas por cliente.
Usado exclusivamente por reportes de cliente.
"""

from src.models.database import db
from src.models.user import User
from src.models.subscription import ClientSubscription
from src.models.plan import Plan


def get_users_by_client(client_id: int) -> int:
    """
    Retorna la cantidad de usuarios asociados a un cliente.
    """
    return (
        db.session.query(User)
        .filter(User.client_id == client_id)
        .count()
    )


def get_active_services_by_client(client_id: int) -> int:
    """
    Retorna la cantidad de servicios activos del cliente.
    """
    return (
        db.session.query(ClientSubscription)
        .filter(
            ClientSubscription.client_id == client_id,
            ClientSubscription.is_active.is_(True)
        )
        .count()
    )


def get_client_plan(client_id: int) -> str | None:
    """
    Retorna el código del plan activo del cliente.
    """
    result = (
        db.session.query(Plan.code)
        .join(ClientSubscription, ClientSubscription.plan_id == Plan.id)
        .filter(
            ClientSubscription.client_id == client_id,
            ClientSubscription.is_active.is_(True)
        )
        .first()
    )

    return result[0] if result else None

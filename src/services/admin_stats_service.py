"""
ADMIN STATS SERVICE
===================

Servicio de estadísticas globales para administración (root / admin).

IMPORTANTE:
- Todas las métricas representan CLIENTES (empresas),
  no usuarios individuales.
- Los usuarios se gestionan en admin_users_service.
"""

from sqlalchemy import func
from src.models.database import db
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan


def get_admin_stats() -> dict:
    """
    Retorna estadísticas globales del sistema para vistas y reportes admin.
    """

    total_clients = Client.query.count()
    active_clients = Client.query.filter_by(is_active=True).count()
    inactive_clients = total_clients - active_clients

    clients_by_plan = (
        db.session.query(
            Plan.name.label("plan"),
            func.count(ClientSubscription.id).label("count")
        )
        .join(ClientSubscription, ClientSubscription.plan_id == Plan.id)
        .filter(ClientSubscription.is_active.is_(True))
        .group_by(Plan.name)
        .all()
    )

    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "inactive_clients": inactive_clients,
        "clients_by_plan": [
            {"plan": plan, "count": count}
            for plan, count in clients_by_plan
        ]
    }

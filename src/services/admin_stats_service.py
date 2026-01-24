"""
ADMIN STATS SERVICE
===================

Servicio de estadísticas globales para administración (root / admin).

IMPORTANTE:
- Todas las métricas representan USUARIOS.
- El contrato debe coincidir EXACTAMENTE con AdminDashboard.
"""

from sqlalchemy import func
from src.models.database import db
from src.models.user import User
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan


def get_admin_stats() -> dict:
    """
    Retorna estadísticas globales del sistema para dashboard admin.

    Contrato:
    {
        total_users: number,
        active_users: number,
        inactive_users: number,
        users_by_plan: [{ plan: string, count: number }]
    }
    """

    # ==============================
    # USUARIOS
    # ==============================

    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    inactive_users = total_users - active_users

    # ==============================
    # USUARIOS POR PLAN
    # (usuarios asociados a clientes con plan activo)
    # ==============================

    users_by_plan = (
        db.session.query(
            Plan.name.label("plan"),
            func.count(User.id).label("count")
        )
        .join(ClientSubscription, ClientSubscription.plan_id == Plan.id)
        .join(Client, Client.id == ClientSubscription.client_id)
        .join(User, User.client_id == Client.id)
        .filter(ClientSubscription.is_active.is_(True))
        .filter(User.is_active.is_(True))
        .group_by(Plan.name)
        .order_by(func.count(User.id).desc())
        .all()
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "users_by_plan": [
            {"plan": plan, "count": count}
            for plan, count in users_by_plan
        ],
    }

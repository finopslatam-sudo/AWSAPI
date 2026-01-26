"""
ADMIN STATS SERVICE
===================

Servicio de estadísticas globales para administración (root / admin).

IMPORTANTE:
- Las métricas representan ENTIDADES del sistema (clientes, usuarios, planes).
- El contrato está diseñado para AdminDashboard.
"""

from sqlalchemy import func, distinct
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
        companies: {
            total: number,
            inactive: number
        },
        users: {
            clients: number,
            admins: number,
            root: number,
            inactive: number
        },
        plans: {
            in_use: number,
            usage: [{ plan: string, count: number }]
        }
    }
    """

def get_users_by_client(client_id: int) -> int:
    """
    Retorna la cantidad de usuarios asociados a un cliente.

    Usado por:
    - src/reports/client/client_stats_provider.py

    IMPORTANTE:
    - No filtra por estado para no romper reportes existentes
    """
    from src.models.user import User

    return (
        User.query
        .filter(User.client_id == client_id)
        .count()
    )
def get_active_services_by_client(client_id: int) -> int:
    """
    Retorna la cantidad de servicios activos de un cliente.

    En el modelo actual, un "servicio activo" corresponde
    a una suscripción activa (client_subscriptions.is_active = True).
    """
    from src.models.subscription import ClientSubscription

    return (
        ClientSubscription.query
        .filter(
            ClientSubscription.client_id == client_id,
            ClientSubscription.is_active.is_(True)
        )
        .count()
    )
def get_client_plan(client_id: int) -> str | None:
    """
    Retorna el código del plan activo del cliente.

    - Si el cliente tiene una suscripción activa → retorna plan.code
    - Si no tiene plan activo → retorna None

    Usado por:
    - src/reports/client/client_stats_provider.py
    """

    from src.models.subscription import ClientSubscription
    from src.models.plan import Plan

    result = (
        db.session.query(Plan.code)
        .join(
            ClientSubscription,
            ClientSubscription.plan_id == Plan.id
        )
        .filter(
            ClientSubscription.client_id == client_id,
            ClientSubscription.is_active.is_(True)
        )
        .first()
    )

    return result[0] if result else None

    # ==============================
    # EMPRESAS (clients)
    # ==============================

    total_companies = db.session.query(Client).count()

    inactive_companies = (
        db.session.query(Client)
        .filter(Client.is_active.is_(False))
        .count()
    )

    # ==============================
    # USUARIOS (users)
    # ==============================

    client_users = (
        db.session.query(User)
        .filter(User.client_role.isnot(None))
        .count()
    )

    admin_users = (
        db.session.query(User)
        .filter(User.global_role == "admin")
        .count()
    )

    root_users = (
        db.session.query(User)
        .filter(User.global_role == "root")
        .count()
    )

    inactive_users = (
        db.session.query(User)
        .filter(User.is_active.is_(False))
        .count()
    )

    # ==============================
    # PLANES EN USO
    # (no existe plans.is_active)
    # ==============================

    plans_in_use = (
        db.session.query(distinct(ClientSubscription.plan_id))
        .filter(
            (ClientSubscription.is_active.is_(True))
        )
        .count()
    )

    plans_usage = (
        db.session.query(
            Plan.code.label("plan"),
            func.count(ClientSubscription.client_id).label("count")
        )
        .join(
            ClientSubscription,
            ClientSubscription.plan_id == Plan.id
        )
        .filter(ClientSubscription.is_active.is_(True))
        .group_by(Plan.code)
        .order_by(func.count(ClientSubscription.client_id).desc())
        .all()
    )

    return {
        "companies": {
            "total": total_companies,
            "inactive": inactive_companies,
        },
        "users": {
            "clients": client_users,
            "admins": admin_users,
            "root": root_users,
            "inactive": inactive_users,
        },
        "plans": {
            "in_use": plans_in_use,
            "usage": [
                {"plan": plan, "count": count}
                for plan, count in plans_usage
            ],
        },
    }

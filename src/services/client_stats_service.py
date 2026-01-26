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


    # ==============================
    # EMPRESAS (clients)
    # ==============================

    total_companies = Client.query.count()

    inactive_companies = (
        Client.query
        .filter(
            (Client.is_active.is_(False)) |
            (Client.is_active.is_(None))
        )
        .count()
    )

    # ==============================
    # USUARIOS (users)
    # ==============================

    client_users = (
        User.query
        .filter(User.client_role.isnot(None))
        .count()
    )

    admin_users = (
        User.query
        .filter(User.global_role == "admin")
        .count()
    )

    root_users = (
        User.query
        .filter(User.global_role == "root")
        .count()
    )

    inactive_users = (
        User.query
        .filter(
            (User.is_active.is_(False)) |
            (User.is_active.is_(None))
        )
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

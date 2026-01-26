"""
ADMIN OVERVIEW SERVICE
======================

Métricas ejecutivas globales para dashboard admin.
"""

from sqlalchemy import func, distinct
from src.models.database import db
from src.models.user import User
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan


def get_admin_overview() -> dict:

    total_companies = db.session.query(Client).count()
    inactive_companies = (
        db.session.query(Client)
        .filter(Client.is_active.is_(False))
        .count()
    )

    client_users = (
        db.session.query(User)
        .filter(User.client_id.isnot(None))
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

    plans_in_use = (
        db.session.query(distinct(ClientSubscription.plan_id))
        .filter(ClientSubscription.is_active.is_(True))
        .count()
    )

    plans_usage = (
        db.session.query(
            Plan.code.label("plan"),
            func.count(ClientSubscription.client_id).label("count")
        )
        .join(ClientSubscription, ClientSubscription.plan_id == Plan.id)
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

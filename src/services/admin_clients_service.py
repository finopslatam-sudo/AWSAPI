"""
ADMIN CLIENTS SERVICE

Este servicio maneja vistas administrativas de clientes
y su suscripción activa a planes FinOps.

NO manejar usuarios aquí.
Los usuarios se gestionan exclusivamente desde:
- admin_users_routes.py
- User model
"""
from sqlalchemy.orm import aliased
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan
from src.models.database import db


def get_clients_with_active_plan():
    ActiveSubscription = aliased(ClientSubscription)

    rows = (
        db.session.query(
            Client.id,
            Client.company_name,
            Client.contact_name,
            Client.email,
            Client.is_active,
            Plan.name.label("plan"),
        )
        .outerjoin(
            ActiveSubscription,
            (ActiveSubscription.client_id == Client.id)
            & (ActiveSubscription.is_active.is_(True))
        )
        .outerjoin(
            Plan,
            Plan.id == ActiveSubscription.plan_id
        )
        .order_by(Client.created_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "company_name": r.company_name,
            "contact_name": r.contact_name,
            "email": r.email,
            "is_active": r.is_active,
            "plan": r.plan,  # None si no tiene suscripción activa
        }
        for r in rows
    ]

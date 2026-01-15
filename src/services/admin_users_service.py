from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan
from src.models.database import db


# =====================================================
# (USO OPERACIONAL / BILLING)
# =====================================================
def get_all_users_with_plan():
    rows = (
        db.session.query(
            Client.id,
            Client.company_name,
            Client.email,
            Client.role,
            Client.is_active,
            Plan.name.label("plan")
        )
        .join(ClientSubscription, ClientSubscription.client_id == Client.id)
        .join(Plan, Plan.id == ClientSubscription.plan_id)
        .order_by(Client.created_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "company_name": r.company_name,
            "email": r.email,
            "role": r.role,
            "is_active": r.is_active,
            "plan": r.plan,
        }
        for r in rows
    ]


# =====================================================
# ADMIN VIEW — TODOS LOS USUARIOS (CON O SIN PLAN)
# =====================================================
def get_all_users_admin_view():
    rows = (
        db.session.query(
            Client.id,
            Client.company_name,
            Client.contact_name,
            Client.email,
            Client.role,
            Client.is_active,
            Client.is_root,
            Plan.name.label("plan")
        )
        .outerjoin(
            ClientSubscription,
            ClientSubscription.client_id == Client.id
        )
        .outerjoin(
            Plan,
            Plan.id == ClientSubscription.plan_id
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
            "role": r.role,
            "is_active": r.is_active,
            "is_root": r.is_root,
            "plan": r.plan,  # puede ser None (admin / root)
        }
        for r in rows
    ]

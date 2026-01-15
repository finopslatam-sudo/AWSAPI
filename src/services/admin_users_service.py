from sqlalchemy.orm import aliased
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan
from src.models.database import db


def get_all_users_with_plan():
    ActiveSubscription = aliased(ClientSubscription)

    rows = (
        db.session.query(
            Client.id,
            Client.company_name,
            Client.contact_name,
            Client.email,
            Client.role,
            Client.is_active,
            Client.is_root,

            # 🔹 PLAN COMPLETO
            Plan.id.label("plan_id"),
            Plan.code.label("plan_code"),
            Plan.name.label("plan_name"),
        )
        .outerjoin(
            ActiveSubscription,
            (ActiveSubscription.client_id == Client.id)
            & (ActiveSubscription.is_active == True)
        )
        .outerjoin(
            Plan,
            Plan.id == ActiveSubscription.plan_id
        )
        .order_by(Client.created_at.desc())
        .all()
    )

    users = []

    for r in rows:
        users.append({
            "id": r.id,
            "company_name": r.company_name,
            "contact_name": r.contact_name,
            "email": r.email,
            "role": r.role,
            "is_active": r.is_active,
            "is_root": r.is_root,

            # 🔹 OBJETO PLAN (o null)
            "plan": (
                {
                    "id": r.plan_id,
                    "code": r.plan_code,
                    "name": r.plan_name,
                }
                if r.plan_id
                else None
            ),
        })

    return users

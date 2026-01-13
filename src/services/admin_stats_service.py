from src.models.database import db
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan

def get_total_users():
    return db.session.query(Client).count()


def get_active_users():
    return db.session.query(Client).filter_by(is_active=True).count()


def get_inactive_users():
    return db.session.query(Client).filter_by(is_active=False).count()


def get_users_grouped_by_plan():
    result = (
        db.session.query(
            Plan.name.label("plan_name"),
            db.func.count(ClientSubscription.id).label("count")
        )
        .join(ClientSubscription, ClientSubscription.plan_id == Plan.id)
        .group_by(Plan.name)
        .all()
    )

    return [
        {
            "plan": row.plan_name,
            "count": row.count
        }
        for row in result
    ]

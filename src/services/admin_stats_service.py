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
def get_admin_stats():
    total_users = Client.query.count()
    active_users = Client.query.filter_by(is_active=True).count()
    inactive_users = total_users - active_users

    users_by_plan = (
        db.session.query(
            Plan.name.label("plan"),
            db.func.count(ClientSubscription.id).label("count")
        )
        .join(ClientSubscription, ClientSubscription.plan_id == Plan.id)
        .filter(ClientSubscription.is_active == True)
        .group_by(Plan.name)
        .all()
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "users_by_plan": [
            {"plan": plan, "count": count}
            for plan, count in users_by_plan
        ]
    }

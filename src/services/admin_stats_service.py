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
            ClientSubscription.tier,
            db.func.count(ClientSubscription.id).label("count")
        )
        .group_by(ClientSubscription.tier)
        .all()
    )

    return [
        {
            "plan": row.tier.value if row.tier else "unknown",
            "count": row.count
        }
        for row in result
    ]

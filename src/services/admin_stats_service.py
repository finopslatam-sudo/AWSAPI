from models.database import db
from models.client import Client
from models.subscription import Subscription
from models.aws_account import AWSAccount


def get_total_users():
    return db.session.query(Client).count()


def get_active_users():
    return db.session.query(Client).filter_by(active=True).count()


def get_inactive_users():
    return db.session.query(Client).filter_by(active=False).count()


def get_users_grouped_by_plan():
    result = (
        db.session.query(
            Subscription.plan_name,
            db.func.count(Subscription.id)
        )
        .group_by(Subscription.plan_name)
        .all()
    )

    return [
        {"plan": row[0], "count": row[1]}
        for row in result
    ]

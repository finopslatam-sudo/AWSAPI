from src.models.client import Client
from src.models.subscription import Subscription
from src.models.aws_account import AWSAccount
from src.models.database import db


def get_users_by_client(client_id: int):
    return (
        db.session.query(Client)
        .filter_by(id=client_id)
        .count()
    )


def get_active_services_by_client(client_id: int):
    return (
        db.session.query(AWSAccount)
        .filter_by(client_id=client_id, active=True)
        .count()
    )


def get_client_plan(client_id: int):
    plan = (
        db.session.query(Subscription.plan_name)
        .filter_by(client_id=client_id)
        .first()
    )
    return plan[0] if plan else "Sin plan"

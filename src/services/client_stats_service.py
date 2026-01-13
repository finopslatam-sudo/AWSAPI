from src.models.client import Client
from src.models.subscription import ClientSubscription
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
    subscription = (
        ClientSubscription.query
        .filter_by(client_id=client_id, is_active=True)
        .first()
    )

    if not subscription or not subscription.tier:
        return None

    return subscription.tier.value

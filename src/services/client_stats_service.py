from src.models.database import db
from src.models.client import Client
from src.models.aws_account import AWSAccount


def get_users_by_client(client_id: int):
    return (
        db.session.query(Client)
        .filter(Client.id == client_id)
        .count()
    )


def get_active_services_by_client(client_id: int):
    return (
        db.session.query(AWSAccount)
        .filter(
            AWSAccount.client_id == client_id,
            AWSAccount.active.is_(True)
        )
        .count()
    )

"""
CLIENT STATS SERVICE
====================

Servicio de estadísticas para vistas y reportes del cliente.

IMPORTANTE:
- Todas las métricas están estrictamente filtradas por client_id
- No maneja usuarios internos del cliente
- No expone información de otros clientes
"""
from src.models.database import db
from src.models.client import Client
from src.models.aws_account import AWSAccount
from src.models.subscription import ClientSubscription
from src.models.plan import Plan


def get_users_by_client(client_id: int) -> int:
    return (
        db.session.query(Client)
        .filter_by(id=client_id)
        .count()
    )


def get_active_services_by_client(client_id: int) -> int:
    return (
        db.session.query(AWSAccount)
        .filter_by(client_id=client_id, is_active=True)
        .count()
    )


def get_client_plan(client_id: int) -> str | None:
    row = (
        db.session.query(Plan.name)
        .join(ClientSubscription, ClientSubscription.plan_id == Plan.id)
        .filter(
            ClientSubscription.client_id == client_id,
            ClientSubscription.is_active == True
        )
        .first()
    )

    return row.name if row else None

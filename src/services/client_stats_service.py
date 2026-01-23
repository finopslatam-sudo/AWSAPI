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


def get_active_aws_accounts(client_id: int) -> int:
    """
    Retorna la cantidad de cuentas AWS activas del cliente.
    """
    return (
        db.session.query(AWSAccount)
        .filter_by(client_id=client_id, active=True)
        .count()
    )


def get_active_client_plan(client_id: int) -> str | None:
    """
    Retorna el nombre del plan activo del cliente, si existe.
    """
    row = (
        db.session.query(Plan.name)
        .join(ClientSubscription, ClientSubscription.plan_id == Plan.id)
        .filter(
            ClientSubscription.client_id == client_id,
            ClientSubscription.is_active.is_(True)
        )
        .first()
    )

    return row.name if row else None


def get_client_stats(client_id: int) -> dict:
    """
    Retorna estadísticas consolidadas del cliente para reportes y dashboards.
    """

    client = Client.query.get(client_id)

    if not client:
        raise ValueError("Cliente no encontrado")

    return {
        "client_id": client.id,
        "company_name": client.company_name,
        "is_active": client.is_active,
        "plan": get_active_client_plan(client_id),
        "active_aws_accounts": get_active_aws_accounts(client_id),
    }

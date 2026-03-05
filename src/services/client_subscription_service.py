"""
CLIENT SUBSCRIPTION SERVICE
===========================

Obtiene información del plan actual del cliente.
"""

from src.models.subscription import ClientSubscription
from src.models.plan import Plan


def get_client_subscription(client_id: int):

    subscription = (
        ClientSubscription.query
        .filter_by(
            client_id=client_id,
            is_active=True
        )
        .first()
    )

    if not subscription:
        return None

    plan = Plan.query.get(subscription.plan_id)

    return {
        "plan_id": plan.id,
        "plan_code": plan.code,
        "plan_name": plan.name
    }
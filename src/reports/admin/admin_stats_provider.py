"""
ADMIN STATS PROVIDER
====================

Provee estadísticas administrativas de CLIENTES
y su suscripción activa a planes FinOps.

IMPORTANTE:
- No maneja usuarios
- No maneja roles
- No maneja autenticación
"""

from sqlalchemy.orm import aliased
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan
from src.models.database import db


# =====================================================
# CLIENTES CON PLAN ACTIVO (O SIN PLAN)
# =====================================================
def get_clients_with_plan():
    ActiveSubscription = aliased(ClientSubscription)

    rows = (
        db.session.query(
            Client.id,
            Client.company_name,
            Client.contact_name,
            Client.email,
            Client.is_active,
            Plan.name.label("plan"),
        )
        .outerjoin(
            ActiveSubscription,
            (ActiveSubscription.client_id == Client.id)
            & (ActiveSubscription.is_active.is_(True))
        )
        .outerjoin(
            Plan,
            Plan.id == ActiveSubscription.plan_id
        )
        .order_by(Client.created_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "company_name": r.company_name,
            "contact_name": r.contact_name,
            "email": r.email,
            "is_active": r.is_active,
            "plan": r.plan,  # None si no tiene plan activo
        }
        for r in rows
    ]


# =====================================================
# FUNCIÓN CONSUMIDA POR REPORTES ADMIN
# =====================================================
def get_admin_stats():
    """
    Retorna estadísticas administrativas para reportes.
    """
    return {
        "clients": get_clients_with_plan()
    }

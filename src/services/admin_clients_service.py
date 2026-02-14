"""
ADMIN CLIENTS SERVICE
=====================

Este servicio maneja vistas administrativas de clientes
y su suscripción activa a planes FinOps.

IMPORTANTE:
- NO maneja usuarios como dominio
- PERO puede DERIVAR información a partir de ellos
  para construir vistas administrativas (read models)

Los usuarios se gestionan exclusivamente desde:
- admin_users_routes.py
- User model
"""

from sqlalchemy.orm import aliased

from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan
from src.models.user import User
from src.models.database import db


# =====================================================
# CONSTANTES
# =====================================================

SYSTEM_ROLES = ("root", "admin", "support")


# =====================================================
# SERVICE
# =====================================================
def get_clients_with_active_plan():
    """
    Retorna listado único de clientes con su plan activo.
    Versión optimizada y libre de duplicados.
    """

    # -------------------------------------------------
    # Subquery: suscripción activa única por cliente
    # -------------------------------------------------
    active_sub = (
        db.session.query(ClientSubscription)
        .filter(ClientSubscription.is_active.is_(True))
        .subquery()
    )

    # -------------------------------------------------
    # Subquery: clientes que tienen usuarios del sistema
    # -------------------------------------------------
    system_clients = (
        db.session.query(User.client_id)
        .filter(User.global_role.in_(SYSTEM_ROLES))
        .distinct()
        .subquery()
    )

    # -------------------------------------------------
    # Query principal
    # -------------------------------------------------
    rows = (
        db.session.query(
            Client.id,
            Client.company_name,
            Client.contact_name,
            Client.email,
            Client.phone,
            Client.is_active,
            Client.created_at,
            Plan.name.label("plan"),
            system_clients.c.client_id.label("is_system_client"),
        )
        .outerjoin(active_sub, active_sub.c.client_id == Client.id)
        .outerjoin(Plan, Plan.id == active_sub.c.plan_id)
        .outerjoin(system_clients, system_clients.c.client_id == Client.id)
        .order_by(Client.created_at.desc())
        .all()
    )

    # -------------------------------------------------
    # Construcción response
    # -------------------------------------------------
    response = []

    for r in rows:
        response.append({
            "id": r.id,
            "company_name": r.company_name,
            "contact_name": r.contact_name,
            "email": r.email,
            "phone": r.phone,
            "is_active": r.is_active,
            "plan": r.plan,
            "created_at": (
                r.created_at.isoformat()
                if r.created_at else None
            ),
            "is_system": r.is_system_client is not None,
        })

    return response

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
    Retorna listado de clientes para panel administrativo.

    Incluye:
    - datos básicos del cliente
    - nombre del plan activo (si existe)
    - flag calculado `is_system`

    NOTAS:
    - NO expone usuarios
    - NO persiste `is_system`
    - `is_system` se deriva desde User.global_role
    """

    ActiveSubscription = aliased(ClientSubscription)

    # -------------------------------------------------
    # Query principal de clientes + plan activo
    # (1 fila por cliente)
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
        .group_by(
            Client.id,
            Client.company_name,
            Client.contact_name,
            Client.email,
            Client.phone,
            Client.is_active,
            Client.created_at,
            Plan.name,
        )
        .order_by(Client.created_at.desc())
        .all()
    )

    # -------------------------------------------------
    # Construcción del response
    # -------------------------------------------------
    response = []

    for r in rows:
        # Determinar si el cliente es del sistema
        is_system = (
            db.session.query(User.id)
            .filter(
                User.client_id == r.id,
                User.global_role.in_(SYSTEM_ROLES)
            )
            .first()
            is not None
        )

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
            "is_system": is_system,
        })

    return response

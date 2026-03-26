"""
PLAN PERMISSIONS
================

Define qué módulos del SaaS están habilitados
según el plan del cliente.

Este módulo también define límites operacionales
según el plan contratado.

Diseño enterprise:
- Separación entre plan comercial y plan interno
- Feature gating centralizado
- Límites por plan
"""

from typing import Optional

from src.models.subscription import ClientSubscription
from src.models.plan import Plan


# =====================================================
# PLAN CODE MAPPING (BD → INTERNAL)
# =====================================================

PLAN_CODE_MAP = {
    "FINOPS_FOUNDATION": "foundation",
    "FINOPS_PROFESSIONAL": "professional",
    "FINOPS_ENTERPRISE": "enterprise"
}


# =====================================================
# FEATURE MATRIX
# =====================================================

PLAN_FEATURES = {

    "foundation": {

        "findings": True,
        "assets": True,
        "costos": True,
        "alertas": False,

        "gobernanza": False,
        "optimization": False,

    },

    "professional": {

        "findings": True,
        "assets": True,
        "costos": True,
        "alertas": False,

        "gobernanza": True,
        "optimization": True,

    },

    "enterprise": {

        "findings": True,
        "assets": True,
        "costos": True,
        "alertas": True,

        "gobernanza": True,
        "optimization": True,

    }
}


# =====================================================
# PLAN LIMITS
# =====================================================

PLAN_LIMITS = {

    "foundation": {
        "aws_accounts": 1,
        "users": 3
    },

    "professional": {
        "aws_accounts": 5,
        "users": 9
    },

    "enterprise": {
        "aws_accounts": 10,
        "users": 12
    }
}


# =====================================================
# GET CLIENT PLAN (INTERNAL CODE)
# =====================================================

def get_client_plan(client_id: int) -> Optional[str]:
    """
    Obtiene el código interno del plan del cliente.

    Convierte el plan comercial almacenado en la BD
    (FINOPS_*) al código interno usado por el sistema.
    """

    if not client_id:
        return None

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

    if not plan:
        return None

    return PLAN_CODE_MAP.get(plan.code)


# =====================================================
# FEATURE CHECK
# =====================================================

def has_feature(client_id: int, feature: str) -> bool:
    """
    Verifica si el plan del cliente tiene habilitada
    una funcionalidad específica del SaaS.
    """

    plan_code = get_client_plan(client_id)

    if not plan_code:
        return False

    features = PLAN_FEATURES.get(plan_code)

    if not features:
        return False

    return features.get(feature, False)


# =====================================================
# GET PLAN LIMIT
# =====================================================

def get_plan_limit(client_id: int, limit_name: str) -> int:
    """
    Retorna el límite permitido para un recurso
    según el plan del cliente.

    Ejemplos:
    - users
    - aws_accounts
    """

    plan_code = get_client_plan(client_id)

    if not plan_code:
        return 0

    limits = PLAN_LIMITS.get(plan_code)

    if not limits:
        return 0

    return limits.get(limit_name, 0)

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
#
# Único plan comercial: FinOps Enterprise. Todo cliente
# (nuevo o existente, sin importar el plan_code que tenga
# en la BD) tiene siempre el set completo de features.
# =====================================================

PLAN_FEATURES = {
    "findings": True,
    "assets": True,
    "costos": True,
    "alertas": True,
    "gobernanza": True,
    "optimization": True,
}


# =====================================================
# PLAN LIMITS
# =====================================================

PLAN_LIMITS = {
    "aws_accounts": 10,
    "azure_accounts": 10,
    "gcp_accounts": 10,
    "users": 12,
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

    Único plan comercial (Enterprise): todo feature está
    habilitado para todo cliente activo.
    """
    return PLAN_FEATURES.get(feature, False)


# =====================================================
# GET PLAN LIMIT
# =====================================================

def get_plan_limit(client_id: int, limit_name: str) -> int:
    """
    Retorna el límite permitido para un recurso.

    Ejemplos:
    - users
    - aws_accounts

    Único plan comercial (Enterprise): el límite es el
    mismo para todo cliente activo.
    """
    return PLAN_LIMITS.get(limit_name, 0)

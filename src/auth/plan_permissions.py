"""
PLAN PERMISSIONS
================

Define qué módulos del SaaS están habilitados
según el plan del cliente.
"""

from src.models.subscription import ClientSubscription
from src.models.plan import Plan


# =====================================================
# FEATURE MATRIX
# =====================================================

PLAN_FEATURES = {

    "foundation": {

        "findings": True,
        "assets": True,
        "costos": True,

        "gobernanza": False,
        "optimization": False,

    },

    "professional": {

        "findings": True,
        "assets": True,
        "costos": True,
        "gobernanza": True,
        "optimization": True,

    },

    "enterprise": {

        "findings": True,
        "assets": True,
        "costos": True,
        "gobernanza": True,
        "optimization": True,

    }
}

# =====================================================
# GET CLIENT PLAN
# =====================================================

def get_client_plan(client_id: int):

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

    return plan.code


# =====================================================
# FEATURE CHECK
# =====================================================

def has_feature(client_id: int, feature: str) -> bool:

    plan_code = get_client_plan(client_id)

    if not plan_code:
        return False

    features = PLAN_FEATURES.get(plan_code, {})

    return features.get(feature, False) is True

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
        "aws_accounts": 20,
        "users": 12
    }
}


# =====================================================
# GET PLAN LIMIT
# =====================================================

def get_plan_limit(client_id: int, limit_name: str):

    plan_code = get_client_plan(client_id)

    if not plan_code:
        return 0

    limits = PLAN_LIMITS.get(plan_code, {})

    return limits.get(limit_name, 0)
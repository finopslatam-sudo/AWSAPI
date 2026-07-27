"""
MFA POLICY
==========

Determina si un usuario debe tener MFA activo según su rol global
o la política MFA configurada a nivel de cliente.
"""

from __future__ import annotations

from typing import Any

from src.models.client import Client
from src.models.user import User

SYSTEM_MFA_ROLES = {"root", "admin"}
CLIENT_ADMIN_ROLES = {"owner", "finops_admin"}


def get_client_mfa_policy(user: User) -> str:
    if user.global_role in SYSTEM_MFA_ROLES:
        return "required"

    if not user.client_id:
        return "disabled"

    client = Client.query.get(user.client_id)
    if not client or not client.is_active:
        return "disabled"

    if client.mfa_policy in Client.MFA_POLICIES:
        return client.mfa_policy

    return "disabled"


def is_mfa_required_for_user(user: User) -> bool:
    policy = get_client_mfa_policy(user)

    if policy == "required":
        return True

    if policy == "required_for_admins":
        return user.client_role in CLIENT_ADMIN_ROLES or bool(user.mfa_enabled)

    if policy == "optional":
        return bool(user.mfa_enabled)

    return False


def must_enroll_mfa(user: User) -> bool:
    policy = get_client_mfa_policy(user)

    if user.global_role in SYSTEM_MFA_ROLES:
        return not user.mfa_enabled

    if policy == "required":
        return not user.mfa_enabled

    if policy == "required_for_admins" and user.client_role in CLIENT_ADMIN_ROLES:
        return not user.mfa_enabled

    return False


def can_disable_mfa(user: User) -> bool:
    policy = get_client_mfa_policy(user)

    if user.global_role in SYSTEM_MFA_ROLES:
        return False

    if policy == "required":
        return False

    if policy == "required_for_admins" and user.client_role in CLIENT_ADMIN_ROLES:
        return False

    return True


def get_mfa_status(user: User) -> dict[str, Any]:
    policy = get_client_mfa_policy(user)
    return {
        "policy": policy,
        "enabled": bool(user.mfa_enabled),
        "required_now": is_mfa_required_for_user(user) or must_enroll_mfa(user),
        "can_disable": can_disable_mfa(user),
        "has_recovery_codes": bool(user.mfa_recovery_codes_hash),
        "confirmed_at": (
            user.mfa_confirmed_at.isoformat()
            if user.mfa_confirmed_at else None
        ),
        "last_used_at": (
            user.mfa_last_used_at.isoformat()
            if user.mfa_last_used_at else None
        ),
    }

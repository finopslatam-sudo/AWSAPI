"""
AUTH PERMISSIONS
================

Capa central de autorización del backend.

Este módulo valida:

GLOBAL ROLES
- root
- admin
- support

CLIENT ROLES
- owner
- finops_admin
- viewer

Todas las rutas del backend deben usar
estas funciones para validar permisos.
"""

from src.models.user import User


# =====================================================
# GLOBAL STAFF
# =====================================================

def require_staff(user_id: int) -> User | None:
    """
    Permite acceso a staff del sistema.

    Roles válidos:
    - root
    - admin
    - support
    """

    user = User.query.get(user_id)

    if not user:
        return None

    if not user.is_active:
        return None

    if user.global_role not in ("root", "admin", "support"):
        return None

    return user


# =====================================================
# GLOBAL ADMIN
# =====================================================

def require_admin(user_id: int) -> User | None:
    """
    Permite acceso solo a admin o root.
    """

    user = User.query.get(user_id)

    if not user:
        return None

    if not user.is_active:
        return None

    if user.global_role not in ("root", "admin"):
        return None

    return user


# =====================================================
# CLIENT USER
# =====================================================

def require_client_user(user_id: int) -> User | None:
    """
    Permite cualquier usuario cliente activo.

    Roles válidos:
    - owner
    - finops_admin
    - viewer
    """

    user = User.query.get(user_id)

    if not user:
        return None

    if not user.is_active:
        return None

    if not user.client_id:
        return None

    if user.client_role not in ("owner", "finops_admin", "viewer"):
        return None

    return user


# =====================================================
# CLIENT ADMIN
# =====================================================

def require_client_admin(user_id: int) -> User | None:
    """
    Permite administración del tenant.

    Roles válidos:
    - owner
    - finops_admin
    """

    user = User.query.get(user_id)

    if not user:
        return None

    if not user.is_active:
        return None

    if not user.client_id:
        return None

    if user.client_role not in ("owner", "finops_admin"):
        return None

    return user


# =====================================================
# CLIENT OWNER
# =====================================================

def require_client_owner(user_id: int) -> User | None:
    """
    Permite solo al owner del tenant.
    """

    user = User.query.get(user_id)

    if not user:
        return None

    if not user.is_active:
        return None

    if not user.client_id:
        return None

    if user.client_role != "owner":
        return None

    return user
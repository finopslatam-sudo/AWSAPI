"""
AUTH PERMISSIONS (RESERVED)

Este módulo está reservado para una futura
centralización de permisos (RBAC).

Actualmente, las validaciones de autorización
se realizan directamente en cada route,
según el contrato del backend.

Roles válidos del sistema:
- root
- admin
- client

NO utilizar este módulo en producción
hasta que se implemente una capa
centralizada de permisos.
"""

from src.models.user import User


def require_admin(user_id: int) -> User | None:
    """
    Retorna el usuario si tiene rol admin o root.
    Uso futuro (no activo actualmente).
    """
    user = User.query.get(user_id)
    if not user:
        return None

    if user.global_role not in ("root", "admin"):
        return None

    return user

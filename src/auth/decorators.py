# =====================================================
#   AUTH DECORATORS — ownership de cliente reutilizable
# =====================================================
# Consolida el patrón repetido en rutas de cliente:
#   identity = get_jwt_identity()
#   user = User.query.get(identity)
#   if not user: return 404 ...
#   if user.client_role not in (...): return 403 ...
#
# Uso:
#   @client_bp.route(...)
#   @jwt_required()
#   @require_client_user_role()
#   def handler(user):
#       ...
from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from src.models.user import User


def require_client_user(user_id: int) -> User | None:
    """Devuelve el usuario si es un usuario de cliente activo, o None."""
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return None

    # No debe ser staff
    if user.global_role is not None:
        return None

    # Debe tener cliente asociado
    if not user.client_id:
        return None

    return user


def require_client_user_role(allowed_roles: list[str] | None = None):
    """
    Decorator para rutas `/api/client/*`: resuelve el usuario desde el JWT,
    valida que sea un usuario de cliente activo (y opcionalmente que su
    `client_role` esté en `allowed_roles`), e inyecta `user` como primer
    argumento posicional del view. Requiere `@jwt_required()` aplicado antes.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user = require_client_user(int(get_jwt_identity()))
            if not user:
                return jsonify({"error": "User not found"}), 404

            if allowed_roles and user.client_role not in allowed_roles:
                return jsonify({"error": "Unauthorized"}), 403

            return view_func(user, *args, **kwargs)
        return wrapper
    return decorator

"""
CLIENT USER ROUTES
==================

Gestión de usuarios dentro de una organización cliente.
Solo el OWNER puede administrar usuarios.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.client_users_service import get_client_users


client_users_bp = Blueprint(
    "client_users",
    __name__,
    url_prefix="/api/client/users"
)


def require_owner(user_id):

    user = User.query.get(user_id)

    if not user:
        return None

    if not user.is_active:
        return None

    if user.client_role != "owner":
        return None

    return user


@client_users_bp.route("", methods=["GET"])
@jwt_required()
def list_client_users():

    actor = require_owner(int(get_jwt_identity()))

    if not actor:
        return jsonify({"error": "Forbidden"}), 403

    users = get_client_users(actor.client_id)

    return jsonify({
        "data": users,
        "meta": {
            "total": len(users)
        }
    }), 200
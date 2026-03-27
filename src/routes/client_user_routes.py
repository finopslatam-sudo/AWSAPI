"""
CLIENT USER ROUTES
==================
Gestión de usuarios dentro de una organización cliente.
Solo el OWNER puede administrar usuarios.
"""

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.client_users_service import get_client_users
from src.services.user_events_service import on_admin_reset_password, on_user_deactivated, on_user_reactivated
from src.auth.plan_permissions import get_plan_limit
from src.services.client_user_management_service import (
    create_client_user,
    update_client_user,
    deactivate_client_user,
    reset_client_user_password,
    activate_client_user,
)


client_users_bp = Blueprint("client_users", __name__, url_prefix="/api/client/users")


def require_owner(user_id: int):
    user = User.query.get(user_id)
    if not user or not user.is_active or not user.client_id or user.client_role != "owner":
        return None
    return user


@client_users_bp.route("", methods=["GET"])
@jwt_required()
def list_client_users():
    actor = require_owner(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Forbidden"}), 403

    users = get_client_users(actor.client_id)
    user_limit = get_plan_limit(actor.client_id, "users")
    return jsonify({
        "data": users,
        "meta": {
            "total": len(users),
            "limit": user_limit,
            "remaining": max(user_limit - len(users), 0),
        },
    }), 200


@client_users_bp.route("", methods=["POST"])
@jwt_required()
def create_client_user_route():
    actor = require_owner(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    name = data.get("name")
    email = data.get("email")
    role = data.get("role")
    password = data.get("password")

    if not all([name, email, role, password]):
        return jsonify({"error": "Missing fields"}), 400

    try:
        result = create_client_user(actor, name, email, role, password)
    except ValueError as e:
        msg = str(e)
        if msg.startswith("user_limit_reached:"):
            limit = msg.split(":")[1]
            return jsonify({"error": "User limit reached", "limit": int(limit)}), 400
        if msg == "email_exists":
            return jsonify({"error": "Email already exists"}), 400
        return jsonify({"error": "Error interno del servidor"}), 500

    return jsonify({"data": result}), 201


@client_users_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_client_user_route(user_id):
    actor = require_owner(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    try:
        result = update_client_user(actor, user_id, data)
    except ValueError as e:
        msg = str(e)
        if msg == "not_found":
            return jsonify({"error": "User not found"}), 404
        return jsonify({"error": "Forbidden"}), 403

    return jsonify({"data": result}), 200


@client_users_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_client_user(user_id):
    actor = require_owner(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Forbidden"}), 403

    try:
        user = deactivate_client_user(actor, user_id)
    except ValueError as e:
        msg = str(e)
        if msg == "not_found":
            return jsonify({"error": "User not found"}), 404
        if msg == "self_delete":
            return jsonify({"error": "Owner cannot delete itself"}), 400
        return jsonify({"error": "Forbidden"}), 403

    try:
        on_user_deactivated(user)
    except Exception:
        current_app.logger.exception("[CLIENT_USER_DEACTIVATED_EMAIL_FAILED] user_id=%s", user.id)

    return jsonify({"ok": True}), 200


@client_users_bp.route("/<int:user_id>/reset-password", methods=["POST"])
@jwt_required()
def client_reset_password(user_id):
    actor = User.query.get(get_jwt_identity())
    if not actor or actor.client_role != "owner":
        return jsonify({"error": "Unauthorized"}), 403

    try:
        user, temp_password = reset_client_user_password(actor, user_id)
    except ValueError as e:
        msg = str(e)
        if msg == "not_found":
            return jsonify({"error": "User not found"}), 404
        return jsonify({"error": "No pertenece a tu organización"}), 403

    try:
        on_admin_reset_password(user, temp_password)
    except Exception:
        current_app.logger.exception("[CLIENT_RESET_PASSWORD_EMAIL_FAILED] user_id=%s", user.id)

    return jsonify({"ok": True}), 200


@client_users_bp.route("/<int:user_id>/activate", methods=["PATCH"])
@jwt_required()
def activate_user(user_id):
    actor = User.query.get(get_jwt_identity())
    if not actor or actor.client_role != "owner":
        return jsonify({"error": "Unauthorized"}), 403

    try:
        user = activate_client_user(actor, user_id)
    except ValueError as e:
        msg = str(e)
        if msg == "not_found":
            return jsonify({"error": "User not found"}), 404
        return jsonify({"error": "No pertenece a tu organización"}), 403

    try:
        on_user_reactivated(user)
    except Exception:
        current_app.logger.exception("[CLIENT_USER_REACTIVATED_EMAIL_FAILED] user_id=%s", user.id)

    return jsonify({"ok": True}), 200

"""
CLIENT USER ROUTES
==================

Gestión de usuarios dentro de una organización cliente.
Solo el OWNER puede administrar usuarios.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.client_users_service import get_client_users
from src.auth.plan_permissions import get_plan_limit
from src.models.database import db
from src.services.password_service import hash_password
from src.services.email_service import send_email
from src.services.email_templates import build_user_welcome_email

client_users_bp = Blueprint(
    "client_users",
    __name__,
    url_prefix="/api/client/users"
)

# =====================================================
# requiere owner
# =====================================================
def require_owner(user_id: int):

    user = User.query.get(user_id)

    if not user:
        return None

    # usuario desactivado
    if not user.is_active:
        return None

    # no pertenece a cliente
    if not user.client_id:
        return None

    # rol incorrecto
    if user.client_role != "owner":
        return None

    return user

# =====================================================
# Lista Usuarios de clientes
# =====================================================
@client_users_bp.route("", methods=["GET"])
@jwt_required()
def list_client_users():

    actor = require_owner(int(get_jwt_identity()))

    if not actor:
        return jsonify({
            "error": "Forbidden"
        }), 403

    users = get_client_users(actor.client_id)

    user_limit = get_plan_limit(actor.client_id, "users")

    return jsonify({
        "data": users,
        "meta": {
            "total": len(users),
            "limit": user_limit,
            "remaining": max(user_limit - len(users), 0)
        }
    }), 200

# =====================================================
# Crea usuario de cliente + correo de bienvenia
# =====================================================
@client_users_bp.route("", methods=["POST"])
@jwt_required()
def create_client_user():

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

    # verificar email existente
    existing = User.query.filter_by(email=email).first()

    if existing:
        return jsonify({"error": "Email already exists"}), 400

    new_user = User(
        contact_name=name,
        email=email,
        password_hash=hash_password(password),
        client_id=actor.client_id,
        client_role=role,
        is_active=True,
        force_password_change=True
    )

    db.session.add(new_user)
    db.session.commit()

    # email bienvenida
    try:

        email_body = build_user_welcome_email(
            name=name,
            email=email,
            password=password
        )

        send_email(
            to=email,
            subject="Bienvenido a FinOpsLatam",
            body=email_body
        )

    except Exception as e:
        print("Error sending welcome email:", e)

    return jsonify({
        "data": {
            "id": new_user.id,
            "email": new_user.email,
            "role": new_user.client_role
        }
    }), 201

# =====================================================
# Edita Usuario de cliente
# =====================================================
@client_users_bp.route("/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_client_user(user_id):

    actor = require_owner(int(get_jwt_identity()))

    if not actor:
        return jsonify({"error": "Forbidden"}), 403

    user = User.query.get(user_id)

    if not user or user.client_id != actor.client_id:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}

    user.contact_name = data.get("name", user.contact_name)
    user.email = data.get("email", user.email)
    user.client_role = data.get("role", user.client_role)

    db.session.commit()

    return jsonify({
        "data": "updated"
    }), 200
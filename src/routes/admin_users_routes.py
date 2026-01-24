# =====================================================
# ADMIN USERS ROUTES
# =====================================================

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.database import db
from src.models.user import User
from src.models.client import Client
from src.services.password_service import generate_temp_password
from src.services.user_events_service import (
    on_user_deactivated,
    on_user_reactivated,
    on_admin_reset_password,
)

# =====================================================
# BLUEPRINT
# =====================================================
admin_users_bp = Blueprint(
    "admin_users",
    __name__,
    url_prefix="/api/admin"
)


def register_admin_users_routes(app):
    app.register_blueprint(admin_users_bp)


# =====================================================
# HELPERS
# =====================================================
def require_staff(user_id: int) -> User | None:
    user = User.query.get(user_id)
    if not user:
        return None
    if user.global_role not in ("root", "admin"):
        return None
    return user

# =====================================================
# ADMIN — LISTAR USUARIOS
# =====================================================
@admin_users_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users():
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Acceso denegado"}), 403

    rows = (
        db.session.query(
            User.id,
            User.email,
            User.global_role,
            User.client_role,
            User.client_id,
            User.is_active,
            User.force_password_change,
            Client.company_name,
        )
        .outerjoin(Client, User.client_id == Client.id)
        .order_by(User.id.asc())
        .all()
    )

    return jsonify({
        "users": [
            {
                "id": r.id,
                "email": r.email,
                "global_role": r.global_role,
                "client_role": r.client_role,
                "client_id": r.client_id,
                "company_name": r.company_name,
                "is_active": r.is_active,
                "force_password_change": r.force_password_change,
            }
            for r in rows
        ]
    }), 200

# =====================================================
# ADMIN — CREAR USUARIO
# =====================================================
@admin_users_bp.route("", methods=["POST"])
@jwt_required()
def create_user():
    """
    Crea un usuario asociado a un cliente.
    """

    actor = User.query.get(int(get_jwt_identity()))

    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}

    email = data.get("email")
    client_id = data.get("client_id")
    client_role = data.get("client_role")

    # ==========================
    # VALIDATION
    # ==========================
    if not email:
        return jsonify({"error": "email es obligatorio"}), 400

    if not client_id:
        return jsonify({"error": "client_id es obligatorio"}), 400

    if client_role not in ("owner", "finops_admin", "viewer"):
        return jsonify({"error": "client_role inválido"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "El usuario ya existe"}), 409

    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Cliente no existe"}), 404

    # ==========================
    # CREATE USER
    # ==========================
    temp_password = generate_temp_password()

    user = User(
        email=email,
        global_role=None,
        client_id=client_id,
        client_role=client_role,
        is_active=True,
        force_password_change=True,
    )

    user.set_password(temp_password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "id": user.id,
        "email": user.email,
        "client_id": user.client_id,
        "client_role": user.client_role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }), 201

# =====================================================
# ADMIN — ACTIVAR / DESACTIVAR USUARIO
# =====================================================
@admin_users_bp.route("/users/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id: int):
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Acceso denegado"}), 403

    target = User.query.get(user_id)
    if not target:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # 🚫 no tocar root desde support
    if actor.global_role == "support" and target.global_role == "root":
        return jsonify({"error": "No puedes modificar un usuario root"}), 403

    # 🚫 no auto-desactivarse
    if actor.id == target.id:
        return jsonify({"error": "No puedes modificarte a ti mismo"}), 403

    data = request.get_json() or {}

    previous_state = target.is_active
    target.is_active = data.get("is_active", target.is_active)

    db.session.commit()

    # 📧 eventos
    if previous_state and not target.is_active:
        on_user_deactivated(target)

    if not previous_state and target.is_active:
        on_user_reactivated(target)

    return jsonify({"message": "Usuario actualizado"}), 200


# =====================================================
# ADMIN — RESET PASSWORD
# =====================================================
@admin_users_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@jwt_required()
def reset_user_password(user_id: int):
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Acceso denegado"}), 403

    target = User.query.get(user_id)
    if not target:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if actor.global_role == "support" and target.global_role == "root":
        return jsonify({
            "error": "No puedes resetear la contraseña de un usuario root"
        }), 403

    temp_password = generate_temp_password()

    target.set_password(temp_password)
    target.force_password_change = True

    db.session.commit()

    on_admin_reset_password(target, temp_password)

    return jsonify({
        "message": "Contraseña reseteada correctamente"
    }), 200

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
@admin_users_bp.route("/users", methods=["POST"])
@jwt_required()
def create_user():
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Acceso denegado"}), 403

    data = request.get_json() or {}

    email = data.get("email")
    global_role = data.get("global_role")  # root | support | None
    client_id = data.get("client_id")
    client_role = data.get("client_role")  # owner | finops_admin | viewer

    if not email:
        return jsonify({"error": "email es obligatorio"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Ya existe un usuario con ese email"}), 409

    # ----------------------------
    # VALIDACIÓN DE ROLES
    # ----------------------------
    if global_role and global_role not in ("root", "support"):
        return jsonify({"error": "global_role inválido"}), 400

    if client_role and client_role not in (
        "owner",
        "finops_admin",
        "viewer",
    ):
        return jsonify({"error": "client_role inválido"}), 400

    # ----------------------------
    # VALIDAR CLIENTE (si aplica)
    # ----------------------------
    if client_id:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({"error": "Cliente no encontrado"}), 404
    else:
        client = None

    # ----------------------------
    # CREAR USUARIO
    # ----------------------------
    temp_password = generate_temp_password()

    user = User(
        email=email,
        global_role=global_role,
        client_id=client.id if client else None,
        client_role=client_role,
        is_active=True,
        force_password_change=True,
    )

    user.set_password(temp_password)

    db.session.add(user)
    db.session.commit()

    # 📧 Evento (email + auditoría)
    on_admin_reset_password(user, temp_password)

    return jsonify({
        "id": user.id,
        "email": user.email,
        "global_role": user.global_role,
        "client_role": user.client_role,
        "client_id": user.client_id,
        "is_active": user.is_active,
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

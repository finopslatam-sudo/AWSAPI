# =====================================================
# ADMIN USERS ROUTES
# =====================================================

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

# =====================================================
# MODELS & DB
# =====================================================
from src.models.database import db
from src.models.user import User
from src.models.client import Client

# =====================================================
# SERVICES (EVENTOS / EMAIL / AUDITORÍA)
# =====================================================
from src.services.user_events_service import (
    on_user_deactivated,
    on_admin_reset_password,
    on_user_reactivated
)
from src.services.password_service import generate_temp_password
from src.services.user_events_service import on_forgot_password

# =====================================================
# BLUEPRINT
# =====================================================
admin_users_bp = Blueprint(
    "admin_users",
    __name__,
    url_prefix="/api/admin"
)

# =====================================================
# REGISTRO DEL BLUEPRINT
# =====================================================
def register_admin_users_routes(app):
    app.register_blueprint(admin_users_bp)


# =====================================================
# ADMIN — LISTAR USUARIOS (ROOT / SUPPORT)
# =====================================================
@admin_users_bp.route("/users", methods=["GET"])
@jwt_required()
def admin_list_users():
    user_id = get_jwt_identity()
    admin = User.query.get(user_id)

    if not admin or admin.global_role not in ("root", "support"):
        return jsonify({"msg": "Unauthorized"}), 403

    rows = (
        User.query
        .outerjoin(Client, User.client_id == Client.id)
        .add_columns(
            User.id,
            User.email,
            User.global_role,
            User.client_role,
            User.is_active,
            Client.company_name,
            Client.contact_name,
            Client.email.label("client_email"),
            Client.is_active.label("client_active"),
            Client.is_root
        )
        .all()
    )

    users = []
    for r in rows:
        users.append({
            "id": r.id,
            "email": r.email,
            "global_role": r.global_role,
            "client_role": r.client_role,
            "is_active": r.is_active,
            "company_name": r.company_name,
            "contact_name": r.contact_name,
            "client_email": r.client_email,
            "client_active": r.client_active,
            "is_root": r.is_root
        })

    return jsonify({"users": users}), 200


# =====================================================
# ADMIN — ACTUALIZAR USUARIO
# =====================================================
@admin_users_bp.route("/users/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):
    actor = User.query.get(int(get_jwt_identity()))
    target = User.query.get(user_id)

    if not actor or not actor.is_active:
        return jsonify({"error": "Unauthorized"}), 403

    if not target:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # 🔐 Solo staff
    if actor.global_role not in ("root", "support"):
        return jsonify({"error": "Acceso denegado"}), 403

    # 🚫 Support NO puede modificar root
    if actor.global_role == "support" and target.global_role == "root":
        return jsonify({
            "error": "No puedes modificar un usuario root"
        }), 403

    data = request.get_json() or {}

    previous_state = target.is_active
    target.is_active = data.get("is_active", target.is_active)

    db.session.commit()

    # 📧 Eventos
    if previous_state and not target.is_active:
        on_user_deactivated(target)

    if not previous_state and target.is_active:
        on_user_reactivated(target)

    return jsonify({"message": "Usuario actualizado"}), 200


# =====================================================
# ADMIN — DESACTIVAR USUARIO
# =====================================================
@admin_users_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def deactivate_user(user_id):
    actor = User.query.get(int(get_jwt_identity()))

    if not actor or not actor.is_active:
        return jsonify({"error": "Unauthorized"}), 403

    if actor.global_role not in ("root", "support"):
        return jsonify({"error": "Acceso denegado"}), 403

    target = User.query.get(user_id)
    if not target:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if target.global_role == "root":
        return jsonify({
            "error": "No se puede desactivar un usuario root"
        }), 403

    if actor.id == target.id:
        return jsonify({
            "error": "No puedes desactivarte a ti mismo"
        }), 403

    if not target.is_active:
        return jsonify({
            "message": "Usuario ya estaba desactivado"
        }), 200

    target.is_active = False
    db.session.commit()

    on_user_deactivated(target)

    return jsonify({"status": "ok"}), 200


# =====================================================
# ADMIN — RESET PASSWORD
# =====================================================
@admin_users_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@jwt_required()
def reset_user_password(user_id):
    actor = User.query.get(int(get_jwt_identity()))
    target = User.query.get(user_id)

    if not actor or not actor.is_active:
        return jsonify({"error": "Unauthorized"}), 403

    if not target:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if actor.global_role not in ("root", "support"):
        return jsonify({"error": "Acceso denegado"}), 403

    if actor.global_role == "support" and target.global_role == "root":
        return jsonify({
            "error": "No puedes resetear la contraseña de un usuario root"
        }), 403

    data = request.get_json() or {}
    new_password = data.get("password")

    if not new_password:
        return jsonify({"error": "Contraseña requerida"}), 400

    target.set_password(new_password)
    target.force_password_change = True  # ⚠️ solo si este campo existe en User

    db.session.commit()

    on_admin_reset_password(target, new_password)

    return jsonify({"message": "Contraseña actualizada"}), 200

# =====================================================
# ADMIN — CREAR USUARIO
# =====================================================
@admin_users_bp.route("/users", methods=["POST"])
@jwt_required()
def create_user():
    actor = User.query.get(int(get_jwt_identity()))

    if not actor or actor.global_role not in ("root", "support"):
        return jsonify({"error": "Acceso denegado"}), 403

    data = request.get_json() or {}

    email = data.get("email")
    client_id = data.get("client_id")
    client_role = data.get("client_role")

    if not email or not client_id or not client_role:
        return jsonify({
            "error": "email, client_id y client_role son obligatorios"
        }), 400

    if client_role not in ("owner", "finops_admin", "viewer"):
        return jsonify({"error": "client_role inválido"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Ya existe un usuario con ese email"}), 409

    client = Client.query.get(client_id)
    if not client or not client.is_active:
        return jsonify({"error": "Cliente no válido o inactivo"}), 400

    temp_password = generate_temp_password()

    user = User(
        email=email,
        client_id=client.id,
        client_role=client_role,
        is_active=True,
        force_password_change=True
    )

    user.set_password(temp_password)

    db.session.add(user)
    db.session.commit()

    on_forgot_password(user, temp_password)

    return jsonify({
        "id": user.id,
        "email": user.email,
        "client_id": user.client_id,
        "client_role": user.client_role,
        "is_active": user.is_active
    }), 201

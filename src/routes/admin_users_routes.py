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
    if user.global_role not in ("root", "admin", "support"):
        return None
    return user


def build_admin_user_view(row, actor: User) -> dict:
    """
    Construye la vista administrativa de un usuario
    lista para renderizar en frontend.
    """

    is_global = row.global_role is not None
    role = row.global_role if is_global else row.client_role

    can_edit = True
    if row.global_role == "root":
        can_edit = False
    if actor.global_role == "support" and row.global_role == "root":
        can_edit = False

    return {
        "id": row.id,
        "email": row.email,
        "type": "global" if is_global else "client",
        "role": role,
        "is_active": row.is_active,
        "force_password_change": row.force_password_change,
        "company_name": row.company_name,
        "client": (
            {
                "id": row.client_id,
                "company_name": row.company_name,
            }
            if row.client_id else None
        ),
        "can_edit": can_edit,
    }


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

    data = [build_admin_user_view(r, actor) for r in rows]

    return jsonify({
        "data": data,
        "meta": {
            "total": len(data)
        }
    }), 200


# =====================================================
# ADMIN — CREAR USUARIO (CLIENTE)
# =====================================================

@admin_users_bp.route("", methods=["POST"])
@jwt_required()
def create_user():
    actor = User.query.get(int(get_jwt_identity()))
    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}

    email = data.get("email")
    client_id = data.get("client_id")
    client_role = data.get("client_role")

    if not email:
        return jsonify({"error": "email es obligatorio"}), 400

    if not client_id:
        return jsonify({"error": "client_id es obligatorio"}), 400

    if client_role not in ("owner", "finops_admin", "viewer"):
        return jsonify({"error": "client_role inválido"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "El usuario ya existe"}), 409

    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Cliente no existe"}), 404

    temp_password = generate_temp_password()

    user = User(
        email=email.strip().lower(),
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
        "data": {
            "id": user.id,
            "email": user.email,
            "role": user.client_role,
            "type": "client",
            "company_name": client.company_name,
            "is_active": user.is_active,
        }
    }), 201

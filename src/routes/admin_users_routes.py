# =====================================================
# ADMIN USERS ROUTES — CRUD
# Endpoints: list users, create user, create user with password.
# Update/access endpoints live in admin_user_access_routes.py
# =====================================================
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.database import db
from src.models.user import User
from src.models.client import Client
from src.services.password_service import generate_temp_password
from src.routes.admin_user_helpers import (
    require_staff,
    build_admin_user_view,
    validate_new_user_payload,
    build_global_user,
    build_client_user,
)

# =====================================================
# BLUEPRINT
# =====================================================
admin_users_bp = Blueprint("admin_users", __name__, url_prefix="/api/admin")

# =====================================================
# ADMIN — LISTAR USUARIOS
# =====================================================
@admin_users_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users():
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Acceso denegado"}), 403

    grouped = request.args.get("grouped") == "1"

    # =====================================================
    # MODO 1 — LISTADO PLANO (ACTUAL, NO SE ROMPE)
    # =====================================================
    if not grouped:
        rows = (
            db.session.query(
                User.id,
                User.email,
                User.global_role,
                User.client_role,
                User.client_id,
                User.is_active,
                User.force_password_change,
                User.mfa_enabled,
                User.mfa_confirmed_at,
                User.contact_name,
                Client.company_name,
            )
            .outerjoin(Client, User.client_id == Client.id)
            .order_by(User.id.asc())
            .all()
        )

        data = [build_admin_user_view(r, actor) for r in rows]
        return jsonify({"data": data, "meta": {"total_users": len(data)}}), 200

    # =====================================================
    # MODO 2 — AGRUPADO POR CLIENTE (ENTERPRISE)
    # =====================================================
    clients = Client.query.order_by(Client.id.asc()).all()
    result = []
    total_users = 0

    for client in clients:
        users = (
            db.session.query(User)
            .filter(User.client_id == client.id)
            .order_by(User.id.asc())
            .all()
        )

        users_data = [
            build_admin_user_view(
                type("Row", (), {
                    "id": u.id,
                    "email": u.email,
                    "global_role": u.global_role,
                    "client_role": u.client_role,
                    "client_id": u.client_id,
                    "is_active": u.is_active,
                    "force_password_change": u.force_password_change,
                    "mfa_enabled": u.mfa_enabled,
                    "mfa_confirmed_at": u.mfa_confirmed_at,
                    "contact_name": u.contact_name,
                    "company_name": client.company_name,
                })(),
                actor
            )
            for u in users
        ]

        total_users += len(users_data)
        result.append({
            "client_id": client.id,
            "company_name": client.company_name,
            "plan": getattr(client, "plan_name", None),
            "users": users_data,
        })

    return jsonify({
        "data": result,
        "meta": {"total_clients": len(result), "total_users": total_users},
    }), 200

# =====================================================
# ADMIN — CREAR USUARIO (CLIENTE)
# =====================================================
@admin_users_bp.route("", methods=["POST"])
@jwt_required()
def create_user():
    actor = User.query.get(int(get_jwt_identity()))
    if not actor or not actor.is_active:
        return jsonify({"error": "Unauthorized"}), 403

    if actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}
    contact_name = (data.get("contact_name") or "").strip()

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
        contact_name=contact_name or None,
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

# =====================================================
# ADMIN — CREAR USUARIO (GLOBAL O CLIENTE)
# =====================================================
@admin_users_bp.route("/users/with-password", methods=["POST"])
@jwt_required()
def create_user_with_password():
    actor = User.query.get(int(get_jwt_identity()))
    if not actor or not actor.is_active:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}

    user_type = data.get("type")  # "global" | "client"
    email = (data.get("email") or "").strip().lower()
    contact_name = (data.get("contact_name") or "").strip()
    password = data.get("password")
    password_confirm = data.get("password_confirm")
    force_change = bool(data.get("force_password_change", True))

    validation_error = validate_new_user_payload(
        actor, user_type, email, contact_name, password, password_confirm
    )
    if validation_error:
        return validation_error

    if user_type == "global":
        user, build_error = build_global_user(actor, data, email, contact_name, force_change)
    else:
        user, build_error = build_client_user(actor, data, email, contact_name, force_change)

    if build_error:
        return build_error

    # =====================================================
    # PERSISTENCIA SEGURA
    # =====================================================
    try:
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Error al crear usuario"}), 500

    # =====================================================
    # EVENTO EMAIL (NO BLOQUEANTE)
    # =====================================================
    from src.services.user_events_service import on_user_created_with_password

    try:
        on_user_created_with_password(user, password)
    except Exception:
        current_app.logger.exception(
            "[USER_WELCOME_EMAIL_FAILED] user_id=%s", user.id,
        )

    return jsonify({
        "data": {
            "id": user.id,
            "email": user.email,
            "type": user_type,
            "global_role": user.global_role,
            "client_id": user.client_id,
            "client_role": user.client_role,
            "is_active": user.is_active,
            "force_password_change": user.force_password_change,
        }
    }), 201

# =====================================================
# ADMIN USER ACCESS ROUTES
# Endpoints: update user (PATCH), set password,
# reset password.
# CRUD endpoints live in admin_users_routes.py
# =====================================================
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.database import db
from src.models.user import User
from src.services.password_service import (
    generate_temp_password,
    get_temp_password_expiration,
)
from src.services.user_events_service import on_admin_reset_password
from src.routes.admin_user_helpers import require_staff, can_reset_password

# =====================================================
# BLUEPRINT
# =====================================================
admin_user_access_bp = Blueprint(
    "admin_user_access",
    __name__,
    url_prefix="/api/admin"
)

# =====================================================
# ADMIN — Editar USUARIOS
# =====================================================
@admin_user_access_bp.route("/users/<int:user_id>", methods=["PATCH"])
@jwt_required()
def update_user(user_id):
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    # =====================================================
    # 🔒 BLOQUEOS GLOBALES (APLICA A TODOS)
    # =====================================================

    # ❌ Nadie puede desactivarse a sí mismo
    if actor.id == user.id:
        if "is_active" in data and data["is_active"] is False:
            return jsonify({"error": "No puedes desactivar tu propia cuenta"}), 403

        # ❌ Nadie puede cambiar su propio rol
        if "global_role" in data or "client_role" in data:
            return jsonify({"error": "No puedes modificar tu propio rol"}), 403

    # =====================================================
    # 🟥 ROOT
    # =====================================================
    if actor.global_role == "root":

        # ===== EMAIL =====
        if "email" in data:
            user.email = data["email"]

        # ===== CONTACT NAME =====
        if "contact_name" in data:
            user.contact_name = (data["contact_name"] or "").strip() or None

        # ===== ACTIVE =====
        if "is_active" in data:
            user.is_active = bool(data["is_active"])

        # ===== GLOBAL ROLE =====
        if user.global_role and "global_role" in data:
            user.global_role = data["global_role"]

        # ===== CLIENT ROLE =====
        if not user.global_role and "client_role" in data:
            user.client_role = data["client_role"]

        db.session.commit()
        return jsonify({"ok": True}), 200

    # =====================================================
    # 🟦 ADMIN
    # =====================================================
    if actor.global_role == "admin":

        # ❌ No puede editar root
        if user.global_role == "root":
            return jsonify({"error": "No permitido editar root"}), 403

        # ===== EMAIL =====
        if "email" in data:
            user.email = data["email"]

        # ===== CONTACT NAME =====
        if "contact_name" in data:
            user.contact_name = (data["contact_name"] or "").strip() or None

        # ===== ACTIVE =====
        if "is_active" in data:
            user.is_active = bool(data["is_active"])

        # ===== GLOBAL ROLE =====
        if user.global_role and "global_role" in data:
            new_role = data["global_role"]

            # ❌ No puede asignar root
            if new_role == "root":
                return jsonify({"error": "No permitido asignar rol root"}), 403

            user.global_role = new_role

        # ===== CLIENT ROLE =====
        if not user.global_role and "client_role" in data:
            user.client_role = data["client_role"]

        db.session.commit()
        return jsonify({"ok": True}), 200

    # =====================================================
    # 🟩 SUPPORT
    # =====================================================
    if actor.global_role == "support":

        # ❌ No puede editar cuentas globales
        if user.global_role is not None:
            return jsonify({"error": "No permitido editar cuentas globales"}), 403

        # ===== EMAIL =====
        if "email" in data:
            user.email = data["email"]

        # ===== CONTACT NAME =====
        if "contact_name" in data:
            user.contact_name = (data["contact_name"] or "").strip() or None

        # ===== ACTIVE =====
        if "is_active" in data:
            user.is_active = bool(data["is_active"])

        # ===== CLIENT ROLE =====
        if "client_role" in data:
            new_role = data["client_role"]

            # ❌ Support no puede asignar owner
            if new_role == "owner":
                return jsonify({"error": "No permitido asignar rol owner"}), 403

            user.client_role = new_role

        db.session.commit()
        return jsonify({"ok": True}), 200

    return jsonify({"error": "Rol no autorizado"}), 403

# =====================================================
# ADMIN — RESET PASSWORD MANUAL
# =====================================================
@admin_user_access_bp.route("/users/<int:user_id>/set-password", methods=["POST"])
@jwt_required()
def admin_set_password(user_id):
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)

    if not can_reset_password(actor, user):
        return jsonify({"error": "No tienes permiso para esta acción"}), 403

    data = request.get_json() or {}

    password = data.get("password")
    if not password or len(password) < 8:
        return jsonify({"error": "Password inválida"}), 400

    user.set_password(password)
    user.force_password_change = True
    user.password_expires_at = get_temp_password_expiration()

    db.session.commit()

    current_app.logger.info(
        "[DEBUG] Ejecutando on_admin_reset_password para user_id=%s", user.id
    )

    try:
        on_admin_reset_password(user, password)
    except Exception:
        current_app.logger.exception(
            "[ADMIN_SET_PASSWORD_EMAIL_FAILED] user_id=%s", user.id,
        )

    return jsonify({"ok": True}), 200

# =====================================================
# USER - RECUPERA SU PASSWORD AL INICIAR SESION
# =====================================================
@admin_user_access_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@jwt_required()
def reset_user_password(user_id):
    actor = require_staff(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)

    if not can_reset_password(actor, user):
        return jsonify({"error": "No tienes permiso para esta acción"}), 403

    temp_password = generate_temp_password()

    user.set_password(temp_password)
    user.force_password_change = True
    user.password_expires_at = get_temp_password_expiration()

    db.session.commit()

    try:
        on_admin_reset_password(user, temp_password)
    except Exception:
        current_app.logger.exception(
            "[ADMIN_RESET_PASSWORD_EMAIL_FAILED] user_id=%s", user.id,
        )

    return jsonify({"ok": True}), 200

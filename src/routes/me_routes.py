from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.database import db

me_bp = Blueprint("me", __name__, url_prefix="/api/me")


# =====================================================
# GET /api/me
# DEVUELVE PERFIL DEL USUARIO (COMPATIBLE CON FRONTEND ACTUAL)
# =====================================================
@me_bp.route("", methods=["GET"])
@jwt_required()
def get_me():
    user = User.query.get_or_404(get_jwt_identity())

    return jsonify({
        "id": user.id,
        "email": user.email,
        "global_role": user.global_role,
        "client_role": user.client_role,
        "client_id": user.client_id,
        "is_active": user.is_active,
        "force_password_change": user.force_password_change,
        "contact_name": user.contact_name 
    }), 200
# =====================================================
# PUT /api/me
# ACTUALIZA DATOS EDITABLES DEL PERFIL
# =====================================================
@me_bp.route("", methods=["PUT"])
@jwt_required()
def update_me():
    user = User.query.get_or_404(get_jwt_identity())
    data = request.get_json() or {}

    # ===== EMAIL (editable) =====
    if "email" in data:
        new_email = data["email"].strip().lower()

        if User.query.filter(
            User.email == new_email,
            User.id != user.id
        ).first():
            return jsonify({"error": "Email ya en uso"}), 409

        user.email = new_email

    # ===== CONTACT NAME (editable) =====
    if "contact_name" in data:
        user.contact_name = data["contact_name"].strip()

    db.session.commit()

    return jsonify({
        "email": user.email,
        "contact_name": user.contact_name,
    }), 200


# =====================================================
# POST /api/me/change-password
# CAMBIO DE PASSWORD
# =====================================================
@me_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_my_password():
    user = User.query.get_or_404(get_jwt_identity())
    data = request.get_json() or {}

    if not user.check_password(data.get("current_password")):
        return jsonify({"error": "Password actual incorrecta"}), 400

    new_password = data.get("new_password")

    if not new_password or len(new_password) < 8:
        return jsonify({"error": "Password inválida"}), 400

    user.set_password(new_password)
    user.force_password_change = False
    user.password_expires_at = None

    db.session.commit()

    return jsonify({"ok": True}), 200

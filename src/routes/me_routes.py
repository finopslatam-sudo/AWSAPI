from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.client import Client
from src.models.plan import Plan
from src.models.subscription import ClientSubscription
from src.models.database import db

from src.services.password_service import validate_password_policy

me_bp = Blueprint("me", __name__, url_prefix="/api/me")

# =====================================================
# GET /api/me
# DEVUELVE PERFIL COMPLETO DEL USUARIO
# =====================================================
@me_bp.route("", methods=["GET"])
@jwt_required()
def get_me():
    user = User.query.get_or_404(get_jwt_identity())

    client = None
    plan = None

    if user.client_id:
        client = Client.query.get(user.client_id)

        subscription = (
            ClientSubscription.query
            .filter_by(client_id=user.client_id, is_active=True)
            .first()
        )

        if subscription:
            plan = Plan.query.get(subscription.plan_id)

    return jsonify({
        "id": user.id,
        "email": user.email,
        "global_role": user.global_role,
        "client_role": user.client_role,
        "client_id": user.client_id,
        "is_active": user.is_active,
        "force_password_change": user.force_password_change,
        "contact_name": user.contact_name,
        "company_name": client.company_name if client else None,
        "plan": {
            "id": plan.id,
            "code": plan.code,
            "name": plan.name
        } if plan else None
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

    return jsonify({"ok": True}), 200


# =====================================================
# USER - CAMBIA SU PASSWORD VOLUNTARIAMENTE
# =====================================================
@me_bp.route("", methods=["GET"])
@jwt_required()
def get_me():
    user = User.query.get_or_404(get_jwt_identity())

    return jsonify({
        "id": user.id,
        "email": user.email,
        "global_role": user.global_role,
        "contact_name": user.contact_name,
        "is_active": user.is_active,
        "force_password_change": user.force_password_change,
    }), 200


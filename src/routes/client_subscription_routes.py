"""
CLIENT SUBSCRIPTION ROUTES
==========================

Devuelve información del plan actual del cliente.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.client_subscription_service import get_client_subscription
from src.models.subscription import ClientSubscription
from src.models.plan import Plan
from src.models.database import db

from src.services.client_subscription_service import get_client_subscription

from src.services.email_service import send_email
from src.services.email_templates import (
    build_plan_changed_email,
    build_internal_plan_upgrade_alert
)


client_subscription_bp = Blueprint(
    "client_subscription",
    __name__,
    url_prefix="/api/client/subscription"
)


@client_subscription_bp.route("", methods=["GET"])
@jwt_required()
def get_subscription():

    user = User.query.get(int(get_jwt_identity()))

    if not user:
        return jsonify({"error": "Unauthorized"}), 403

    if not user.is_active:
        return jsonify({"error": "Unauthorized"}), 403

    if not user.client_id:
        return jsonify({"error": "Unauthorized"}), 403

    subscription = get_client_subscription(user.client_id)

    return jsonify({
        "data": subscription
    }), 200

# =====================================================
# POST /api/client/subscription/upgrade
# UPGRADE DE PLAN (SOLO OWNER)
# =====================================================

@client_subscription_bp.route("/upgrade", methods=["POST"])
@jwt_required()
def upgrade_subscription():

    user = User.query.get(int(get_jwt_identity()))

    if not user or not user.client_id:
        return jsonify({"error": "Unauthorized"}), 403

    if user.client_role != "owner":
        return jsonify({"error": "Only owner can upgrade plan"}), 403

    data = request.get_json() or {}
    new_plan_code = data.get("plan_code")

    if not new_plan_code:
        return jsonify({"error": "Missing plan_code"}), 400

    # =====================================
    # OBTENER SUSCRIPCIÓN ACTUAL
    # =====================================

    subscription = (
        ClientSubscription.query
        .filter_by(
            client_id=user.client_id,
            is_active=True
        )
        .first()
    )

    if not subscription:
        return jsonify({"error": "Subscription not found"}), 404

    current_plan = Plan.query.get(subscription.plan_id)

    new_plan = Plan.query.filter_by(code=new_plan_code).first()

    if not new_plan:
        return jsonify({"error": "Invalid plan"}), 400

    # =====================================
    # PREVENIR DOWNGRADE
    # =====================================

    plan_order = {
        "FINOPS_FOUNDATION": 1,
        "FINOPS_PROFESSIONAL": 2,
        "FINOPS_ENTERPRISE": 3
    }

    if plan_order[new_plan.code] <= plan_order[current_plan.code]:
        return jsonify({"error": "Downgrade not allowed"}), 400

    # =====================================
    # ACTUALIZAR PLAN
    # =====================================

    subscription.plan_id = new_plan.id
    db.session.commit()

    # =====================================
    # EMAIL CLIENTE
    # =====================================

    client_email_body = build_plan_changed_email(
        name=user.contact_name,
        old_plan_name=current_plan.name,
        new_plan_name=new_plan.name
    )

    send_email(
        to=user.email,
        subject="FinOpsLatam — Cambio de plan",
        body=client_email_body
    )

    # =====================================
    # EMAIL ALERTA INTERNA
    # =====================================

    internal_body = build_internal_plan_upgrade_alert(
        name=user.contact_name,
        client_id=user.client_id,
        email=user.email,
        old_plan=current_plan.name,
        new_plan=new_plan.name
    )

    send_email(
        to="contacto@finopslatam.com",
        subject="FinOpsLatam — Upgrade de plan realizado",
        body=internal_body
    )

    # =====================================
    # RESPUESTA
    # =====================================

    return jsonify({
        "status": "ok",
        "new_plan": new_plan.name
    }), 200
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

from src.services.email_service import send_email
from src.services.email_templates import (
    build_internal_plan_upgrade_alert,
    build_plan_upgrade_request_received_email
)

from src.models.plan_upgrade_request import PlanUpgradeRequest


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
    # PREVENIR SOLICITUD DUPLICADA
    # =====================================

    existing_request = PlanUpgradeRequest.query.filter_by(
        client_id=user.client_id,
        status="PENDING"
    ).first()

    if existing_request:
        return jsonify({
            "error": "Upgrade request already pending"
        }), 400

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
    # CREAR SOLICITUD DE UPGRADE
    # =====================================

    upgrade_request = PlanUpgradeRequest(
        client_id=user.client_id,
        requested_plan=new_plan.code,
        requested_by_user_id=user.id,
        status="PENDING"
    )

    db.session.add(upgrade_request)

    db.session.commit()

    # =====================================
    # EMAIL AL OWNER CONFIRMANDO SOLICITUD
    # =====================================

    try:

        owner_email_body = build_plan_upgrade_request_received_email(
            name=user.contact_name,
            client_id=user.client_id,
            email=user.email,
            old_plan_name=current_plan.name,
            new_plan_name=new_plan.name,
            new_plan=new_plan.name
        )

        send_email(
            to=user.email,
            subject="FinOpsLatam — Solicitud de upgrade recibida",
            body=owner_email_body
        )

    except Exception as e:
        print("Error sending owner email:", e)

    # =====================================
    # EMAIL ALERTA INTERNA A ADMIN
    # =====================================
    try:

        admin_body = build_internal_plan_upgrade_alert(
            name=user.contact_name,
            client_id=user.client_id,
            email=user.email,
            old_plan=current_plan.name,
            new_plan=new_plan.name
        )

        send_email(
            to="contacto@finopslatam.com",
            subject="FinOpsLatam — Nueva solicitud de upgrade",
            body=admin_body
        )

    except Exception as e:
        print("Error sending admin email:", e)

    # =====================================
    # RESPUESTA
    # =====================================
    return jsonify({
        "data": {
            "status": "pending",
            "requested_plan": new_plan.name,
            "message": "Upgrade request created"
        }
    }), 200
"""
CLIENT INFO ROUTES
==================

Información general de la organización cliente.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from src.auth.decorators import require_client_user_role
from src.models.client import Client
from src.models.aws_account import AWSAccount
from src.models.subscription import ClientSubscription
from src.models.plan import Plan


client_info_bp = Blueprint(
    "client_info",
    __name__,
    url_prefix="/api/client"
)


@client_info_bp.route("", methods=["GET"])
@jwt_required()
@require_client_user_role()
def get_client_info(user):

    # ==========================
    # CLIENT DATA
    # ==========================

    client = Client.query.get(user.client_id)

    if not client:
        return jsonify({"error": "Client not found"}), 404

    # ==========================
    # SUBSCRIPTION
    # ==========================

    subscription = (
        ClientSubscription.query
        .filter_by(
            client_id=client.id,
            is_active=True
        )
        .first()
    )

    plan_name = None
    plan_code = None

    if subscription:
        plan = Plan.query.get(subscription.plan_id)

        if plan:
            plan_name = plan.name
            plan_code = plan.code

    # ==========================
    # AWS ACCOUNTS
    # ==========================

    aws_accounts_count = (
        AWSAccount.query
        .filter_by(
            client_id=client.id,
            is_active=True
        )
        .count()
    )

    # ==========================
    # RESPONSE
    # ==========================

    return jsonify({

        # ---- compatibilidad con frontend actual ----
        "company_name": client.company_name,
        "email": client.email,
        "contact_name": client.contact_name,
        "phone": client.phone,
        "pais": client.pais,

        # ---- datos estructurados enterprise ----
        "data": {

            "client": {
                "id": client.id,
                "company_name": client.company_name,
                "email": client.email,
                "contact_name": client.contact_name,
                "phone": client.phone,
                "pais": client.pais,
                "created_at": client.created_at.isoformat()
                if client.created_at else None
            },

            "subscription": {
                "plan_name": plan_name,
                "plan_code": plan_code
            },

            "aws_accounts": {
                "total": aws_accounts_count
            }

        }

    }), 200


@client_info_bp.route("/info", methods=["PATCH"])
@jwt_required()
@require_client_user_role(["owner", "finops_admin"])
def update_client_info(user):

    client = Client.query.get(user.client_id)

    if not client:
        return jsonify({"error": "No encontrado"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    if "pais" in data:
        client.pais = str(data["pais"]).strip()[:100] if data["pais"] else None

    if "contact_name" in data:
        client.contact_name = str(data["contact_name"]).strip()[:255] if data["contact_name"] else None

    if "phone" in data:
        client.phone = str(data["phone"]).strip()[:50] if data["phone"] else None

    from src.models.database import db
    db.session.commit()

    return jsonify({
        "pais": client.pais,
        "contact_name": client.contact_name,
        "phone": client.phone,
    }), 200

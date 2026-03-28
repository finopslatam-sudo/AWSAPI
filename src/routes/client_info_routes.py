"""
CLIENT INFO ROUTES
==================

Información general de la organización cliente.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
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
def get_client_info():

    # ==========================
    # USER VALIDATION
    # ==========================

    user = User.query.get(int(get_jwt_identity()))

    if not user:
        return jsonify({"error": "Unauthorized"}), 403

    if not user.is_active:
        return jsonify({"error": "Unauthorized"}), 403

    if not user.client_id:
        return jsonify({"error": "Unauthorized"}), 403

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
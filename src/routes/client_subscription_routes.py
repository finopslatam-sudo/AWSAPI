"""
CLIENT SUBSCRIPTION ROUTES
==========================

Devuelve información del plan actual del cliente.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.client_subscription_service import get_client_subscription


client_subscription_bp = Blueprint(
    "client_subscription",
    __name__,
    url_prefix="/api/client/subscription"
)


@client_subscription_bp.route("", methods=["GET"])
@jwt_required()
def get_subscription():

    user = User.query.get(int(get_jwt_identity()))

    if not user or not user.client_id:
        return jsonify({"error": "Unauthorized"}), 403

    subscription = get_client_subscription(user.client_id)

    return jsonify({
        "data": subscription
    }), 200
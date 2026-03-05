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


client_info_bp = Blueprint(
    "client_info",
    __name__,
    url_prefix="/api/client"
)


@client_info_bp.route("", methods=["GET"])
@jwt_required()
def get_client_info():

    user = User.query.get(int(get_jwt_identity()))

    if not user or not user.client_id:
        return jsonify({"error": "Unauthorized"}), 403

    client = Client.query.get(user.client_id)

    aws_accounts = AWSAccount.query.filter_by(
        client_id=client.id,
        is_active=True
    ).count()

    return jsonify({
        "data": {
            "client_id": client.id,
            "company_name": client.company_name,
            "email": client.email,
            "contact_name": client.contact_name,
            "phone": client.phone,
            "aws_accounts": aws_accounts
        }
    }), 200
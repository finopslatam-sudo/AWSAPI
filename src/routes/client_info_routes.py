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

    if not user:
        return jsonify({"error": "Unauthorized"}), 403

    if not user.is_active:
        return jsonify({"error": "Unauthorized"}), 403

    if not user.client_id:
        return jsonify({"error": "Unauthorized"}), 403
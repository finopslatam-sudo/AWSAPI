from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from src.auth.decorators import require_client_user_role
from src.models.client import Client
from src.models.database import db


client_security_bp = Blueprint("client_security", __name__, url_prefix="/api/client/security")


@client_security_bp.route("", methods=["GET"])
@jwt_required()
@require_client_user_role(["owner"])
def get_client_security(actor):
    client = Client.query.get_or_404(actor.client_id)
    return jsonify({
        "data": {
            "client_id": client.id,
            "company_name": client.company_name,
            "mfa_policy": client.mfa_policy,
            "mfa_updated_at": client.mfa_updated_at.isoformat() if client.mfa_updated_at else None,
        },
    }), 200


@client_security_bp.route("", methods=["PATCH"])
@jwt_required()
@require_client_user_role(["owner"])
def update_client_security(actor):
    data = request.get_json() or {}
    mfa_policy = data.get("mfa_policy")

    if mfa_policy not in Client.MFA_POLICIES:
        return jsonify({"error": "mfa_policy inválida"}), 400

    client = Client.query.get_or_404(actor.client_id)
    client.mfa_policy = mfa_policy
    client.mfa_updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "data": {
            "client_id": client.id,
            "mfa_policy": client.mfa_policy,
            "mfa_updated_at": client.mfa_updated_at.isoformat() if client.mfa_updated_at else None,
        },
    }), 200

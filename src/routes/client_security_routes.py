from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from src.models.client import Client
from src.models.database import db
from src.models.user import User


client_security_bp = Blueprint("client_security", __name__, url_prefix="/api/client/security")


def require_owner(user_id: int):
    user = User.query.get(user_id)
    if not user or not user.is_active or not user.client_id or user.client_role != "owner":
        return None
    return user


@client_security_bp.route("", methods=["GET"])
@jwt_required()
def get_client_security():
    actor = require_owner(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Forbidden"}), 403

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
def update_client_security():
    actor = require_owner(int(get_jwt_identity()))
    if not actor:
        return jsonify({"error": "Forbidden"}), 403

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

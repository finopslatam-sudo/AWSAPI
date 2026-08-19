import os

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.auth.decorators import require_client_user_role
from src.models.user import User
from src.models.gcp_account import GCPAccount
from src.services.gcp_connection_service import GCPConnectionService
from src.auth.plan_permissions import get_plan_limit
from src.models.database import db

client_gcp_connection_bp = Blueprint(
    "client_gcp_connection",
    __name__,
    url_prefix="/api/client/gcp"
)


# ======================================================
# DOWNLOAD DEPLOYMENT MANAGER TEMPLATE (Service Account + rol Viewer)
# ======================================================

@client_gcp_connection_bp.route("/template", methods=["GET"])
def get_deployment_manager_template():

    base_dir = os.path.dirname(os.path.abspath(__file__))

    template_path = os.path.abspath(
        os.path.join(base_dir, "..", "gcp", "templates", "finopslatam_role.yaml")
    )

    return send_file(
        template_path,
        mimetype="application/x-yaml",
        as_attachment=True,
        download_name="finopslatam_role.yaml"
    )


# ======================================================
# VALIDATE + SAVE SERVICE ACCOUNT KEY
# ======================================================

@client_gcp_connection_bp.route("/validate", methods=["POST"])
@jwt_required()
@require_client_user_role(["owner"])
def validate_connection(user):

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    service_account_key = data.get("service_account_key")
    if not service_account_key:
        return jsonify({"error": "Missing data"}), 400

    try:
        account_id = GCPConnectionService.validate_and_save_account(
            client_id=user.client_id,
            service_account_key_raw=service_account_key,
        )
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status": "connected",
        "account_id": account_id
    }), 200


# ======================================================
# GCP CONNECTION STATUS
# ======================================================
@client_gcp_connection_bp.route("/status", methods=["GET"])
@jwt_required()
def gcp_connection_status():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            "status": "disconnected",
            "accounts": [],
            "accounts_limit": 0,
            "accounts_used": 0
        }), 200

    accounts = GCPAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    accounts_used = len(accounts)
    accounts_limit = get_plan_limit(user.client_id, "gcp_accounts")

    status = "connected" if accounts_used > 0 else "disconnected"

    return jsonify({
        "status": status,
        "accounts": [a.to_dict() for a in accounts],
        "accounts_used": accounts_used,
        "accounts_limit": accounts_limit
    }), 200


# ======================================================
# LIST GCP ACCOUNTS
# ======================================================
@client_gcp_connection_bp.route("/accounts", methods=["GET"])
@jwt_required()
@require_client_user_role()
def list_accounts(user):

    accounts = GCPAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    serialized_accounts = [a.to_dict() for a in accounts]

    return jsonify({
        "status": "ok",
        "data": serialized_accounts,
        "accounts": serialized_accounts,
        "total": len(serialized_accounts)
    }), 200


# ======================================================
# DELETE / DISCONNECT GCP ACCOUNT
# ======================================================
@client_gcp_connection_bp.route("/accounts/<int:account_id>", methods=["DELETE"])
@jwt_required()
@require_client_user_role(["owner"])
def delete_account(user, account_id):

    account = GCPAccount.query.filter_by(
        id=account_id, client_id=user.client_id
    ).first()

    if not account:
        return jsonify({"error": "Account not found"}), 404

    account.is_active = False
    db.session.commit()

    return jsonify({"status": "disconnected"}), 200

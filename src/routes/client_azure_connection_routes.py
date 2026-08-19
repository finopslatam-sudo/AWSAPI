import os

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.auth.decorators import require_client_user_role
from src.models.user import User
from src.models.azure_account import AzureAccount
from src.services.azure_connection_service import AzureConnectionService
from src.auth.plan_permissions import get_plan_limit
from src.models.database import db

client_azure_connection_bp = Blueprint(
    "client_azure_connection",
    __name__,
    url_prefix="/api/client/azure"
)


# ======================================================
# DOWNLOAD ARM TEMPLATE (role assignment "Reader")
# ======================================================

@client_azure_connection_bp.route("/template", methods=["GET"])
def get_arm_template():

    base_dir = os.path.dirname(os.path.abspath(__file__))

    template_path = os.path.abspath(
        os.path.join(base_dir, "..", "azure", "templates", "finopslatam_role_assignment.json")
    )

    return send_file(
        template_path,
        mimetype="application/json",
        as_attachment=True,
        download_name="finopslatam_role_assignment.json"
    )


# ======================================================
# VALIDATE + SAVE SERVICE PRINCIPAL
# ======================================================

@client_azure_connection_bp.route("/validate", methods=["POST"])
@jwt_required()
@require_client_user_role(["owner"])
def validate_connection(user):

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    subscription_id = str(data.get("subscription_id", "")).strip()[:36]
    tenant_id = str(data.get("tenant_id", "")).strip()[:36]
    app_client_id = str(data.get("app_client_id", "")).strip()[:36]
    client_secret = str(data.get("client_secret", "")).strip()[:512]

    if not all([subscription_id, tenant_id, app_client_id, client_secret]):
        return jsonify({"error": "Missing data"}), 400

    try:
        account_id = AzureConnectionService.validate_and_save_account(
            client_id=user.client_id,
            subscription_id=subscription_id,
            tenant_id=tenant_id,
            app_client_id=app_client_id,
            client_secret=client_secret,
        )
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status": "connected",
        "account_id": account_id
    }), 200


# ======================================================
# AZURE CONNECTION STATUS
# ======================================================
@client_azure_connection_bp.route("/status", methods=["GET"])
@jwt_required()
def azure_connection_status():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            "status": "disconnected",
            "accounts": [],
            "accounts_limit": 0,
            "accounts_used": 0
        }), 200

    accounts = AzureAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    accounts_used = len(accounts)
    accounts_limit = get_plan_limit(user.client_id, "azure_accounts")

    status = "connected" if accounts_used > 0 else "disconnected"

    return jsonify({
        "status": status,
        "accounts": [a.to_dict() for a in accounts],
        "accounts_used": accounts_used,
        "accounts_limit": accounts_limit
    }), 200


# ======================================================
# LIST AZURE ACCOUNTS
# ======================================================
@client_azure_connection_bp.route("/accounts", methods=["GET"])
@jwt_required()
@require_client_user_role()
def list_accounts(user):

    accounts = AzureAccount.query.filter_by(
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
# DELETE / DISCONNECT AZURE ACCOUNT
# ======================================================
@client_azure_connection_bp.route("/accounts/<int:account_id>", methods=["DELETE"])
@jwt_required()
@require_client_user_role(["owner"])
def delete_account(user, account_id):

    account = AzureAccount.query.filter_by(
        id=account_id, client_id=user.client_id
    ).first()

    if not account:
        return jsonify({"error": "Account not found"}), 404

    account.is_active = False
    db.session.commit()

    return jsonify({"status": "disconnected"}), 200

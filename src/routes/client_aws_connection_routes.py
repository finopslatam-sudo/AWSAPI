from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.aws_connection_service import AWSConnectionService
from src.models.aws_account import AWSAccount
from src.auth.plan_permissions import get_plan_limit

import os

client_aws_connection_bp = Blueprint(
    "client_aws_connection",
    __name__,
    url_prefix="/api/client/aws"
)


# ======================================================
# STEP 1 — GENERATE CLOUDFORMATION LINK
# ======================================================

@client_aws_connection_bp.route("/connect", methods=["POST"])
@jwt_required()
def generate_connection():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.client_role != "owner":
        return jsonify({"error": "Unauthorized"}), 403

    external_id = AWSConnectionService.generate_external_id()

    cloudformation_url = AWSConnectionService.build_cloudformation_url(
        external_id
    )

    return jsonify({
        "external_id": external_id,
        "cloudformation_url": cloudformation_url
    }), 200


# ======================================================
# STEP 2 — VALIDATE ROLE ARN
# ======================================================

@client_aws_connection_bp.route("/validate", methods=["POST"])
@jwt_required()
def validate_connection():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.client_role != "owner":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json

    role_arn = data.get("role_arn")
    external_id = data.get("external_id")

    if not role_arn or not external_id:
        return jsonify({"error": "Missing data"}), 400
    
    # ==========================
    # PLAN LIMIT AWS ACCOUNTS
    # ==========================

    current_accounts = AWSAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).count()

    limit = get_plan_limit(user.client_id, "aws_accounts")

    if current_accounts >= limit:

        return jsonify({
            "error": "AWS account limit reached",
            "limit": limit
        }), 400
    
    account_id = AWSConnectionService.validate_and_save_account(
        client_id=user.client_id,
        role_arn=role_arn,
        external_id=external_id
    )

    return jsonify({
        "status": "connected",
        "account_id": account_id
    }), 200


# ======================================================
# STEP 3 — DOWNLOAD CLOUDFORMATION TEMPLATE
# ======================================================

@client_aws_connection_bp.route("/template", methods=["GET"])
def get_cloudformation_template():

    base_dir = os.path.dirname(os.path.abspath(__file__))

    template_path = os.path.abspath(
        os.path.join(base_dir, "..", "aws", "templates", "finopslatam_role.yaml")
    )

    return send_file(
        template_path,
        mimetype="application/x-yaml",
        as_attachment=True,
        download_name="finopslatam_role.yaml"
    )


# ======================================================
# STEP 4 — AWS CONNECTION STATUS
# ======================================================

@client_aws_connection_bp.route("/status", methods=["GET"])
@jwt_required()
def aws_connection_status():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({
            "status": "disconnected",
            "accounts": []
        }), 200

    accounts = AWSAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    if not accounts:
        return jsonify({
            "status": "disconnected",
            "accounts": []
        }), 200

    return jsonify({
        "status": "connected",
        "accounts": [a.to_dict() for a in accounts]
    }), 200


# ======================================================
# LIST AWS ACCOUNTS
# ======================================================

@client_aws_connection_bp.route("/accounts", methods=["GET"])
@jwt_required()
def list_accounts():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Unauthorized"}), 403

    accounts = AWSAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    return jsonify({
        "accounts": [a.to_dict() for a in accounts]
    }), 200
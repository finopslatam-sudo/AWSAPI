from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

import os
import boto3
from botocore.exceptions import ClientError

from src.models.user import User
from src.models.aws_account import AWSAccount
from src.services.aws_connection_service import AWSConnectionService
from src.aws.sts_service import STSService
from src.auth.plan_permissions import get_plan_limit

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

    account_id = data.get("account_id")
    external_id = data.get("external_id")

    if not account_id or not external_id:
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
        account_id=account_id,
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
            "accounts": [],
            "accounts_limit": 0,
            "accounts_used": 0
        }), 200

    accounts = AWSAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    accounts_used = len(accounts)

    # ==========================
    # PLAN LIMIT
    # ==========================

    accounts_limit = get_plan_limit(user.client_id, "aws_accounts")

    status = "connected" if accounts_used > 0 else "disconnected"

    return jsonify({
        "status": status,
        "accounts": [a.to_dict() for a in accounts],
        "accounts_used": accounts_used,
        "accounts_limit": accounts_limit
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

# ======================================================
# DEBUG AWS CONNECTION
# ======================================================

@client_aws_connection_bp.route("/debug", methods=["POST"])
@jwt_required()
def debug_connection():

    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.client_role != "owner":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json

    account_id = data.get("account_id")
    external_id = data.get("external_id")

    if not account_id or not external_id:
        return jsonify({
            "status": "failed",
            "step": "input_validation",
            "error": "Missing account_id or external_id"
        }), 400

    try:

        role_arn = AWSConnectionService.build_role_arn(account_id)

    except Exception as e:

        return jsonify({
            "status": "failed",
            "step": "build_role_arn",
            "error": str(e)
        }), 400

    try:

        creds = STSService.assume_role(role_arn, external_id)

    except ClientError as e:

        return jsonify({
            "status": "failed",
            "step": "assume_role",
            "error": e.response["Error"]["Code"],
            "message": e.response["Error"]["Message"]
        }), 400

    try:

        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"]
        )

        sts = session.client("sts")

        identity = sts.get_caller_identity()

    except ClientError as e:

        return jsonify({
            "status": "failed",
            "step": "get_caller_identity",
            "error": e.response["Error"]["Code"],
            "message": e.response["Error"]["Message"]
        }), 400

    return jsonify({
        "status": "success",
        "account_id": identity["Account"],
        "arn": identity["Arn"],
        "message": "STS AssumeRole successful"
    }), 200
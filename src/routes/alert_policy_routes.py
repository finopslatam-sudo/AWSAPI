from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.alert_policy_service import AlertPolicyService
from src.auth.plan_permissions import has_feature


alert_policy_bp = Blueprint(
    "alert_policies",
    __name__,
    url_prefix="/api/client/alert-policies"
)

alert_policy_bp.strict_slashes = False


def _parse_threshold(payload):
    try:
        return float(payload["threshold"]) if payload.get("threshold") not in [None, ""] else None
    except (TypeError, ValueError):
        raise ValueError("Invalid threshold")


def _parse_account_id(payload):
    raw_value = payload.get("aws_account_id")
    if raw_value in [None, "", "all"]:
        return None

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        raise ValueError("Invalid aws_account_id")


@alert_policy_bp.route("/", methods=["GET"])
@jwt_required()
def list_policies():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.client_role not in ["owner", "finops_admin", "viewer"]:
        return jsonify({"error": "Unauthorized"}), 403

    if not has_feature(user.client_id, "alertas"):
        return jsonify({"error": "Feature not available in current plan"}), 403

    policies = AlertPolicyService.list_policies(user.client_id)
    return jsonify({
        "status": "ok",
        "data": policies,
        "policies": policies,
        "total": len(policies)
    })


@alert_policy_bp.route("/", methods=["POST"])
@jwt_required()
def create_policy():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.client_role not in ["owner", "finops_admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    if not has_feature(user.client_id, "alertas"):
        return jsonify({"error": "Feature not available in current plan"}), 403

    payload = request.get_json() or {}

    required = ["policy_id", "title", "channel"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        threshold_value = _parse_threshold(payload)
        aws_account_id = _parse_account_id(payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    try:
        policy = AlertPolicyService.create_policy(
            client_id=user.client_id,
            policy_id=payload.get("policy_id"),
            title=payload.get("title"),
            channel=payload.get("channel"),
            email=payload.get("email"),
            threshold=threshold_value,
            threshold_type=payload.get("threshold_type"),
            period=payload.get("period"),
            aws_account_id=aws_account_id,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status": "ok",
        "data": policy,
        "policy": policy
    }), 201


@alert_policy_bp.route("/<int:policy_db_id>", methods=["PUT"])
@jwt_required()
def update_policy(policy_db_id):
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.client_role not in ["owner", "finops_admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    if not has_feature(user.client_id, "alertas"):
        return jsonify({"error": "Feature not available in current plan"}), 403

    payload = request.get_json() or {}

    required = ["policy_id", "title", "channel"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        threshold_value = _parse_threshold(payload)
        aws_account_id = _parse_account_id(payload)
        policy = AlertPolicyService.update_policy(
            client_id=user.client_id,
            policy_db_id=policy_db_id,
            policy_id=payload.get("policy_id"),
            title=payload.get("title"),
            channel=payload.get("channel"),
            email=payload.get("email"),
            threshold=threshold_value,
            threshold_type=payload.get("threshold_type"),
            period=payload.get("period"),
            aws_account_id=aws_account_id,
        )
    except ValueError as e:
        error_message = str(e)
        status_code = 404 if error_message == "Alert policy not found" else 400
        return jsonify({"error": error_message}), status_code

    return jsonify({
        "status": "ok",
        "data": policy,
        "policy": policy
    })


@alert_policy_bp.route("/<int:policy_db_id>", methods=["DELETE"])
@jwt_required()
def delete_policy(policy_db_id):
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.client_role not in ["owner", "finops_admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    if not has_feature(user.client_id, "alertas"):
        return jsonify({"error": "Feature not available in current plan"}), 403

    try:
        AlertPolicyService.delete_policy(client_id=user.client_id, policy_db_id=policy_db_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify({
        "status": "ok",
        "message": "Policy deleted",
        "id": policy_db_id
    })

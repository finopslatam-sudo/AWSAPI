from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.client_findings_service import ClientFindingsService


client_findings_bp = Blueprint(
    "client_findings",
    __name__,
    url_prefix="/api/client"
)


@client_findings_bp.route("/findings", methods=["GET"])
@jwt_required()
def get_client_findings():

    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.client_role not in ["owner", "finops_admin", "viewer"]:
        return jsonify({"error": "Unauthorized"}), 403

    # ---------------- QUERY PARAMS ----------------
    status = request.args.get("status")
    severity = request.args.get("severity")
    finding_type = request.args.get("finding_type")
    search = request.args.get("search")

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")

    result = ClientFindingsService.list_findings(
        client_id=user.client_id,
        status=status,
        severity=severity,
        finding_type=finding_type,
        page=page,
        per_page=per_page,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return jsonify({
        "status": "ok",
        **result
    })


@client_findings_bp.route("/findings/stats", methods=["GET"])
@jwt_required()
def get_client_findings_stats():

    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.client_role not in ["owner", "finops_admin", "viewer"]:
        return jsonify({"error": "Unauthorized"}), 403

    stats = ClientFindingsService.get_stats(user.client_id)

    return jsonify({
        "status": "ok",
        "data": stats
    })

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.client_findings_service import ClientFindingsService
from src.services.client_dashboard_service import ClientDashboardService



client_findings_bp = Blueprint(
    "client_findings",
    __name__,
    url_prefix="/api/client"
)

@client_findings_bp.route("/dashboard/summary", methods=["GET"])
@jwt_required()
def get_dashboard_summary():

    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.client_role not in ["owner", "finops_admin", "viewer"]:
        return jsonify({"error": "Unauthorized"}), 403

    summary = ClientDashboardService.get_summary(user.client_id)
    inventory = ClientDashboardService.get_inventory_summary(user.client_id)

    return jsonify({
        "status": "ok",
        "data": {
            **summary,
            "inventory": inventory
        }
    })

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
@client_findings_bp.route("/findings/<int:finding_id>/resolve", methods=["PATCH"])
@jwt_required()
def resolve_finding(finding_id):

    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Solo owner y finops_admin pueden resolver
    if user.client_role not in ["owner", "finops_admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    finding = ClientFindingsService.resolve_finding(
        client_id=user.client_id,
        finding_id=finding_id,
        user_id=user.id
    )

    if not finding:
        return jsonify({"error": "Finding not found"}), 404

    return jsonify({
        "status": "ok",
        "data": {
            "id": finding.id,
            "resolved": finding.resolved,
            "resolved_at": finding.resolved_at.isoformat() if finding.resolved_at else None,
            "resolved_by": finding.resolved_by
        }
    })
@client_findings_bp.route("/dashboard/costs", methods=["GET"])
@jwt_required()
def get_dashboard_costs():

    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.client_role not in ["owner", "finops_admin", "viewer"]:
        return jsonify({"error": "Unauthorized"}), 403

    data = ClientDashboardService.get_cost_data(user.client_id)

    return jsonify({
        "status": "ok",
        "data": data
    })
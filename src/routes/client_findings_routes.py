from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services.client_findings_service import ClientFindingsService


client_findings_bp = Blueprint("client_findings", __name__, url_prefix="/api/client")


@client_findings_bp.route("/findings", methods=["GET"])
@jwt_required()
def get_client_findings():

    identity = get_jwt_identity()

    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Solo owner / finops_admin / viewer pueden ver
    if user.client_role not in ["owner", "finops_admin", "viewer"]:
        return jsonify({"error": "Unauthorized"}), 403

    status = request.args.get("status")
    severity = request.args.get("severity")
    finding_type = request.args.get("finding_type")

    findings = ClientFindingsService.list_findings(
        client_id=user.client_id,
        status=status,
        severity=severity,
        finding_type=finding_type
    )

    return jsonify({
        "status": "ok",
        "total": len(findings),
        "data": findings
    })

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.aws_account import AWSAccount
from src.models.database import db
from src.aws.finops_auditor import FinOpsAuditor
from datetime import datetime


client_audit_bp = Blueprint(
    "client_audit",
    __name__,
    url_prefix="/api/client"
)


@client_audit_bp.route("/audit/run", methods=["POST"])
@jwt_required()
def run_client_audit():

    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.client_role not in ["owner", "finops_admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    aws_account = AWSAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).first()

    if not aws_account:
        return jsonify({"error": "No active AWS account found"}), 404

    auditor = FinOpsAuditor()

    result = auditor.run_comprehensive_audit(
        client_id=user.client_id,
        aws_account=aws_account
    )

    # Actualizar last_sync
    aws_account.last_sync = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "status": "ok",
        "audit_result": result
    })
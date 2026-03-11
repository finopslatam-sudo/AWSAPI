from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

import threading
import logging
from datetime import datetime

from src.models.database import db
from src.models.user import User
from src.models.aws_account import AWSAccount
from src.aws.finops_auditor import FinOpsAuditor


client_audit_bp = Blueprint(
    "client_audit",
    __name__,
    url_prefix="/api/client/audit"
)

logger = logging.getLogger(__name__)


# =====================================================
# RUN AUDIT
# =====================================================
@client_audit_bp.route("/run", methods=["POST"])
@jwt_required()
def run_client_audit():

    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.client_role not in ["owner", "finops_admin"]:
        return jsonify({"error": "Unauthorized"}), 403

    # Obtener cuenta AWS activa
    aws_account = AWSAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).first()

    if not aws_account:
        return jsonify({"error": "No active AWS account found"}), 404

    # Evitar ejecución simultánea
    if aws_account.audit_status == "running":
        return jsonify({"status": "already_running"}), 200

    # Marcar auditoría como running
    aws_account.audit_status = "running"
    aws_account.audit_started_at = datetime.utcnow()
    aws_account.audit_finished_at = None
    db.session.commit()

    # =====================================================
    # BACKGROUND TASK
    # =====================================================
    def background_audit(app, client_id, aws_account_id):

        with app.app_context():

            try:

                auditor = FinOpsAuditor()

                auditor.run_comprehensive_audit(
                    client_id,
                    aws_account_id
                )

                account = AWSAccount.query.get(aws_account_id)

                account.audit_status = "completed"
                account.audit_finished_at = datetime.utcnow()

                db.session.commit()
                db.session.remove()

                logger.info(
                    f"AUDIT COMPLETED | client_id={client_id}"
                )

            except Exception:

                logger.exception(
                    f"AUDIT FAILED | client_id={client_id}"
                )

                account = AWSAccount.query.get(aws_account_id)

                account.audit_status = "failed"
                account.audit_finished_at = datetime.utcnow()

                db.session.commit()
                db.session.remove()

    # =====================================================
    # RUN THREAD
    # =====================================================
    thread = threading.Thread(
        target=background_audit,
        args=(
            current_app._get_current_object(),
            user.client_id,
            aws_account.id
        ),
        daemon=True
    )

    thread.start()

    return jsonify({"status": "started"}), 202


# =====================================================
# AUDIT STATUS
# =====================================================
@client_audit_bp.route("/status", methods=["GET"])
@jwt_required()
def audit_status():

    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user:
        return jsonify({"error": "User not found"}), 404

    aws_account = AWSAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).first()

    if not aws_account:
        return jsonify({"error": "No AWS account"}), 404

    return jsonify({
        "status": aws_account.audit_status,
        "started_at": aws_account.audit_started_at,
        "finished_at": aws_account.audit_finished_at
    }), 200
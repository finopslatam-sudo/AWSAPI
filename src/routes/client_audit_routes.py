from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from concurrent.futures import ThreadPoolExecutor
import logging
from datetime import datetime

from src.models.database import db
from src.models.user import User
from src.models.aws_account import AWSAccount
from src.aws.finops_auditor import FinOpsAuditor
from src.services.cost_explorer_cache_service import CostExplorerCacheService


client_audit_bp = Blueprint(
    "client_audit",
    __name__,
    url_prefix="/api/client/audit"
)

logger = logging.getLogger(__name__)

audit_executor = ThreadPoolExecutor(max_workers=5)


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
    aws_accounts = AWSAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    if not aws_accounts:
        return jsonify({"error": "No active AWS accounts found"}), 404

    # Evitar ejecución simultánea
    accounts_to_scan = []

    for account in accounts_to_scan:

        if account.audit_status == "running":
            continue

        account.audit_status = "running"
        account.audit_started_at = datetime.utcnow()
        account.audit_finished_at = None

        accounts_to_scan.append(account)

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

                if account:
                    account.audit_status = "completed"
                    account.audit_finished_at = datetime.utcnow()
                    db.session.commit()

                # Invalidar caché de desglose por servicio para que el
                # dashboard refleje los nuevos datos tras el scan.
                CostExplorerCacheService.invalidate_service_breakdown(aws_account_id)

                db.session.remove()

                logger.info(
                    f"AUDIT COMPLETED | client_id={client_id}"
                )

            except Exception as e:

                logger.exception(
                    f"AUDIT FAILED | client_id={client_id}"
                )

                db.session.rollback()

                account = AWSAccount.query.get(aws_account_id)

                if account:
                    account.audit_status = "failed"
                    account.audit_finished_at = datetime.utcnow()
                    db.session.commit()

                db.session.remove()

    # =====================================================
    # RUN THREAD
    # =====================================================
    for account in aws_accounts:

        audit_executor.submit(
            background_audit,
            current_app._get_current_object(),
            user.client_id,
            account.id
        )

    return jsonify({
        "status": "started",
        "accounts_scanning": len(accounts_to_scan)
    }), 202


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

    aws_accounts = AWSAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    if not aws_accounts:
        return jsonify({"error": "No AWS accounts"}), 404

    result = []

    for account in aws_accounts:
        result.append({
            "account_id": account.id,
            "account_name": account.account_name,
            "status": account.audit_status,
            "started_at": account.audit_started_at,
            "finished_at": account.audit_finished_at
        })

    return jsonify(result), 200
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required

from concurrent.futures import ThreadPoolExecutor
import logging
from datetime import datetime

from src.auth.decorators import require_client_user_role
from src.models.database import db
from src.models.gcp_account import GCPAccount
from src.gcp.gcp_auditor import GCPAuditor


client_gcp_audit_bp = Blueprint(
    "client_gcp_audit",
    __name__,
    url_prefix="/api/client/gcp/audit"
)

logger = logging.getLogger(__name__)

gcp_audit_executor = ThreadPoolExecutor(max_workers=5)


# =====================================================
# RUN AUDIT
# =====================================================
@client_gcp_audit_bp.route("/run", methods=["POST"])
@jwt_required()
@require_client_user_role(["owner", "finops_admin"])
def run_client_gcp_audit(user):

    gcp_accounts = GCPAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    if not gcp_accounts:
        return jsonify({"error": "No active GCP accounts found"}), 404

    accounts_to_scan = []

    for account in gcp_accounts:

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
    def background_audit(app, client_id, gcp_account_id):

        with app.app_context():

            try:
                auditor = GCPAuditor()
                auditor.run_comprehensive_audit(client_id, gcp_account_id)

                account = GCPAccount.query.get(gcp_account_id)

                if account:
                    account.audit_status = "completed"
                    account.audit_finished_at = datetime.utcnow()
                    db.session.commit()

                db.session.remove()

                logger.info(f"GCP AUDIT COMPLETED | client_id={client_id}")

            except Exception:

                logger.exception(f"GCP AUDIT FAILED | client_id={client_id}")

                db.session.rollback()

                account = GCPAccount.query.get(gcp_account_id)

                if account:
                    account.audit_status = "failed"
                    account.audit_finished_at = datetime.utcnow()
                    db.session.commit()

                db.session.remove()

    # =====================================================
    # RUN THREAD
    # =====================================================
    for account in accounts_to_scan:

        gcp_audit_executor.submit(
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
@client_gcp_audit_bp.route("/status", methods=["GET"])
@jwt_required()
@require_client_user_role()
def gcp_audit_status(user):

    gcp_accounts = GCPAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    if not gcp_accounts:
        return jsonify({"error": "No GCP accounts"}), 404

    result = []

    for account in gcp_accounts:
        result.append({
            "account_id": account.id,
            "account_name": account.project_name,
            "status": account.audit_status,
            "started_at": account.audit_started_at,
            "finished_at": account.audit_finished_at
        })

    return jsonify(result), 200

from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required

from concurrent.futures import ThreadPoolExecutor
import logging
from datetime import datetime

from src.auth.decorators import require_client_user_role
from src.models.database import db
from src.models.azure_account import AzureAccount
from src.azure.azure_auditor import AzureAuditor


client_azure_audit_bp = Blueprint(
    "client_azure_audit",
    __name__,
    url_prefix="/api/client/azure/audit"
)

logger = logging.getLogger(__name__)

azure_audit_executor = ThreadPoolExecutor(max_workers=5)


# =====================================================
# RUN AUDIT
# =====================================================
@client_azure_audit_bp.route("/run", methods=["POST"])
@jwt_required()
@require_client_user_role(["owner", "finops_admin"])
def run_client_azure_audit(user):

    azure_accounts = AzureAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    if not azure_accounts:
        return jsonify({"error": "No active Azure accounts found"}), 404

    accounts_to_scan = []

    for account in azure_accounts:

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
    def background_audit(app, client_id, azure_account_id):

        with app.app_context():

            try:
                auditor = AzureAuditor()
                auditor.run_comprehensive_audit(client_id, azure_account_id)

                account = AzureAccount.query.get(azure_account_id)

                if account:
                    account.audit_status = "completed"
                    account.audit_finished_at = datetime.utcnow()
                    db.session.commit()

                db.session.remove()

                logger.info(f"AZURE AUDIT COMPLETED | client_id={client_id}")

            except Exception:

                logger.exception(f"AZURE AUDIT FAILED | client_id={client_id}")

                db.session.rollback()

                account = AzureAccount.query.get(azure_account_id)

                if account:
                    account.audit_status = "failed"
                    account.audit_finished_at = datetime.utcnow()
                    db.session.commit()

                db.session.remove()

    # =====================================================
    # RUN THREAD
    # =====================================================
    for account in accounts_to_scan:

        azure_audit_executor.submit(
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
@client_azure_audit_bp.route("/status", methods=["GET"])
@jwt_required()
@require_client_user_role()
def azure_audit_status(user):

    azure_accounts = AzureAccount.query.filter_by(
        client_id=user.client_id,
        is_active=True
    ).all()

    if not azure_accounts:
        return jsonify({"error": "No Azure accounts"}), 404

    result = []

    for account in azure_accounts:
        result.append({
            "account_id": account.id,
            "account_name": account.subscription_name,
            "status": account.audit_status,
            "started_at": account.audit_started_at,
            "finished_at": account.audit_finished_at
        })

    return jsonify(result), 200

import boto3
from datetime import datetime

from src.aws.sts_service import STSService
from src.aws.inventory_scanner import InventoryScanner
from src.aws.finding_engine.finding_engine import FindingEngine
from src.services.risk_snapshot_service import RiskSnapshotService
from src.models.database import db


class FinOpsAuditor:

    # =====================================================
    # MAIN ORCHESTRATOR (ENTERPRISE SAFE)
    # =====================================================
    def run_comprehensive_audit(self, client_id, aws_account):

        # ==========================================
        # 1️⃣ ASSUME ROLE
        # ==========================================
        sts_service = STSService()

        creds = sts_service.assume_role(
            role_arn=aws_account.role_arn,
            external_id=aws_account.external_id,
            session_name="finops-audit"
        )

        if not creds:
            return {
                "status": "error",
                "message": "Unable to assume role",
                "findings_created": 0
            }

        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name="us-east-1"
        )

        findings_created = 0

        try:
            # ==========================================
            # 2️⃣ INVENTORY RECONCILIATION
            # ==========================================
            scanner = InventoryScanner(session, client_id, aws_account)
            scanner.run()

            # ==========================================
            # 3️⃣ RUN FINDING ENGINE
            # ==========================================
            findings_created = FindingEngine.run(client_id)

            # ==========================================
            # 4️⃣ GENERATE RISK SNAPSHOT
            # ==========================================
            RiskSnapshotService.create_snapshot(client_id)

            # ==========================================
            # 5️⃣ UPDATE ACCOUNT LAST SYNC
            # ==========================================
            aws_account.last_sync = datetime.utcnow()
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"[AUDIT PIPELINE ERROR]: {str(e)}")

            return {
                "status": "error",
                "message": "Audit execution failed",
                "findings_created": 0
            }

        return {
            "status": "ok",
            "findings_created": findings_created
        }
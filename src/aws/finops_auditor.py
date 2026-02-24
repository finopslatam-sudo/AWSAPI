import boto3
import logging
from datetime import datetime

from src.aws.sts_service import STSService
from src.aws.inventory_scanner import InventoryScanner
from src.aws.finding_engine.finding_engine import FindingEngine
from src.services.risk_snapshot_service import RiskSnapshotService
from src.models.database import db


logger = logging.getLogger(__name__)


class FinOpsAuditor:

    # =====================================================
    # MAIN ORCHESTRATOR (FULL ENTERPRISE SAFE)
    # =====================================================
    def run_comprehensive_audit(self, client_id, aws_account):

        logger.info(f"Starting audit | client_id={client_id}")

        # ==========================================
        # 1️⃣ ASSUME ROLE
        # ==========================================
        try:
            sts_service = STSService()

            creds = sts_service.assume_role(
                role_arn=aws_account.role_arn,
                external_id=aws_account.external_id,
                session_name="finops-audit"
            )

            if not creds:
                logger.error(f"STS assume_role failed | client_id={client_id}")
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

        except Exception:
            logger.exception(f"STS CRITICAL ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "STS failure",
                "findings_created": 0
            }

        # ==========================================
        # 2️⃣ INVENTORY
        # ==========================================
        try:
            logger.info(f"Inventory scan started | client_id={client_id}")
            scanner = InventoryScanner(session, client_id, aws_account)
            scanner.run()
            logger.info(f"Inventory scan completed | client_id={client_id}")
        except Exception:
            logger.exception(f"INVENTORY ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "Inventory execution failed",
                "findings_created": 0
            }

        # ==========================================
        # 3️⃣ FINDING ENGINE
        # ==========================================
        try:
            logger.info(f"Finding engine started | client_id={client_id}")
            findings_created = FindingEngine.run(client_id)
            logger.info(
                f"Finding engine completed | client_id={client_id} | findings={findings_created}"
            )
        except Exception:
            logger.exception(f"FINDING ENGINE ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "Finding engine execution failed",
                "findings_created": 0
            }

        # ==========================================
        # 4️⃣ SNAPSHOT GENERATION
        # ==========================================
        try:
            logger.info(f"Snapshot generation started | client_id={client_id}")
            RiskSnapshotService.create_snapshot(client_id)
            logger.info(f"Snapshot generation completed | client_id={client_id}")
        except Exception:
            logger.exception(f"SNAPSHOT ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "Snapshot generation failed",
                "findings_created": 0
            }

        # ==========================================
        # 5️⃣ UPDATE ACCOUNT LAST SYNC
        # ==========================================
        try:
            aws_account.last_sync = datetime.utcnow()
            db.session.commit()
        except Exception:
            logger.exception(f"LAST SYNC UPDATE ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "Failed updating last sync",
                "findings_created": 0
            }

        logger.info(f"Audit completed successfully | client_id={client_id}")

        return {
            "status": "ok",
            "findings_created": findings_created
        }
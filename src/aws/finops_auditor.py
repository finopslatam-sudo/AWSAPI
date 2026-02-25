import boto3
import logging
import time
from datetime import datetime

from src.aws.sts_service import STSService
from src.aws.inventory_scanner import InventoryScanner
from src.aws.finding_engine.finding_engine import FindingEngine
from src.services.risk_snapshot_service import RiskSnapshotService
from src.models.database import db
from src.models.aws_account import AWSAccount


logger = logging.getLogger(__name__)


class FinOpsAuditor:

    # =====================================================
    # MAIN ORCHESTRATOR (FULL ENTERPRISE SAFE + TIMING)
    # =====================================================
    def run_comprehensive_audit(self, client_id, aws_account_id):

        audit_start = time.time()
        logger.info(f"AUDIT START | client_id={client_id}")

        # 🔥 Resolver AWSAccount dentro del contexto
        aws_account = AWSAccount.query.get(aws_account_id)

        if not aws_account:
            logger.error(f"AWSAccount not found | client_id={client_id}")
            return {
                "status": "error",
                "message": "AWS account not found",
                "findings_created": 0
            }

        # ==========================================
        # 1️⃣ ASSUME ROLE
        # ==========================================
        try:
            sts_start = time.time()

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

            sts_elapsed = time.time() - sts_start
            logger.info(
                f"STS COMPLETED | client_id={client_id} | duration={sts_elapsed:.2f}s"
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
            inventory_start = time.time()

            logger.info(f"INVENTORY START | client_id={client_id}")
            scanner = InventoryScanner(
                client_id=client_id,
                aws_account_id=aws_account.id
            )
            scanner.run()
            inventory_elapsed = time.time() - inventory_start

            logger.info(
                f"INVENTORY COMPLETED | client_id={client_id} | duration={inventory_elapsed:.2f}s"
            )

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
            findings_start = time.time()

            logger.info(f"FINDING ENGINE START | client_id={client_id}")
            findings_created = FindingEngine.run(client_id)
            findings_elapsed = time.time() - findings_start

            logger.info(
                f"FINDING ENGINE COMPLETED | client_id={client_id} | "
                f"findings={findings_created} | duration={findings_elapsed:.2f}s"
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
            snapshot_start = time.time()

            logger.info(f"SNAPSHOT START | client_id={client_id}")
            RiskSnapshotService.create_snapshot(client_id)
            snapshot_elapsed = time.time() - snapshot_start

            logger.info(
                f"SNAPSHOT COMPLETED | client_id={client_id} | duration={snapshot_elapsed:.2f}s"
            )

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

        audit_elapsed = time.time() - audit_start

        logger.info(
            f"AUDIT COMPLETED SUCCESSFULLY | client_id={client_id} | "
            f"total_duration={audit_elapsed:.2f}s"
        )

        return {
            "status": "ok",
            "findings_created": findings_created,
            "duration_seconds": round(audit_elapsed, 2)
        }
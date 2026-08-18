import logging
import time
from datetime import datetime

from src.gcp.inventory_scanner import GCPInventoryScanner
from src.gcp.finding_engine.finding_engine import GCPFindingEngine
from src.models.database import db
from src.models.gcp_account import GCPAccount


logger = logging.getLogger(__name__)


class GCPAuditor:
    """Equivalente a FinOpsAuditor (AWS) / AzureAuditor, pero para
    cuentas GCP. Sin RiskSnapshot todavía (esa tabla está acoplada a
    AWSFinding)."""

    def run_comprehensive_audit(self, client_id, gcp_account_id):

        audit_start = time.time()
        logger.info(f"GCP AUDIT START | client_id={client_id}")

        gcp_account = GCPAccount.query.get(gcp_account_id)

        if not gcp_account or gcp_account.client_id != client_id:
            logger.error(f"GCPAccount not found | client_id={client_id}")
            return {
                "status": "error",
                "message": "GCP account not found",
                "findings_created": 0
            }

        try:
            inventory_start = time.time()

            scanner = GCPInventoryScanner(
                client_id=client_id,
                gcp_account_id=gcp_account.id
            )
            scanner.run()

            inventory_elapsed = time.time() - inventory_start
            logger.info(
                f"GCP INVENTORY COMPLETED | client_id={client_id} | duration={inventory_elapsed:.2f}s"
            )

        except Exception:
            logger.exception(f"GCP INVENTORY ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "Inventory execution failed",
                "findings_created": 0
            }

        try:
            findings_start = time.time()

            findings_created = GCPFindingEngine.run(client_id)

            findings_elapsed = time.time() - findings_start
            logger.info(
                f"GCP FINDING ENGINE COMPLETED | client_id={client_id} | "
                f"findings={findings_created} | duration={findings_elapsed:.2f}s"
            )

        except Exception:
            logger.exception(f"GCP FINDING ENGINE ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "Finding engine execution failed",
                "findings_created": 0
            }

        try:
            gcp_account.last_sync = datetime.utcnow()
            db.session.commit()
        except Exception:
            logger.exception(f"GCP LAST SYNC UPDATE ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "Failed updating last sync",
                "findings_created": 0
            }

        audit_elapsed = time.time() - audit_start
        logger.info(
            f"GCP AUDIT COMPLETED SUCCESSFULLY | client_id={client_id} | "
            f"total_duration={audit_elapsed:.2f}s"
        )

        return {
            "status": "ok",
            "findings_created": findings_created,
            "duration_seconds": round(audit_elapsed, 2)
        }

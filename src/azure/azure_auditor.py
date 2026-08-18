import logging
import time
from datetime import datetime

from src.azure.inventory_scanner import AzureInventoryScanner
from src.azure.finding_engine.finding_engine import AzureFindingEngine
from src.models.database import db
from src.models.azure_account import AzureAccount


logger = logging.getLogger(__name__)


class AzureAuditor:
    """Equivalente a FinOpsAuditor (AWS), pero para cuentas Azure. No
    incluye generación de RiskSnapshot todavía (esa tabla está acoplada
    a AWSFinding) — queda para una iteración futura si se decide
    extenderla a multi-cloud."""

    def run_comprehensive_audit(self, client_id, azure_account_id):

        audit_start = time.time()
        logger.info(f"AZURE AUDIT START | client_id={client_id}")

        azure_account = AzureAccount.query.get(azure_account_id)

        if not azure_account or azure_account.client_id != client_id:
            logger.error(f"AzureAccount not found | client_id={client_id}")
            return {
                "status": "error",
                "message": "Azure account not found",
                "findings_created": 0
            }

        try:
            inventory_start = time.time()

            scanner = AzureInventoryScanner(
                client_id=client_id,
                azure_account_id=azure_account.id
            )
            scanner.run()

            inventory_elapsed = time.time() - inventory_start
            logger.info(
                f"AZURE INVENTORY COMPLETED | client_id={client_id} | duration={inventory_elapsed:.2f}s"
            )

        except Exception:
            logger.exception(f"AZURE INVENTORY ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "Inventory execution failed",
                "findings_created": 0
            }

        try:
            findings_start = time.time()

            findings_created = AzureFindingEngine.run(client_id)

            findings_elapsed = time.time() - findings_start
            logger.info(
                f"AZURE FINDING ENGINE COMPLETED | client_id={client_id} | "
                f"findings={findings_created} | duration={findings_elapsed:.2f}s"
            )

        except Exception:
            logger.exception(f"AZURE FINDING ENGINE ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "Finding engine execution failed",
                "findings_created": 0
            }

        try:
            azure_account.last_sync = datetime.utcnow()
            db.session.commit()
        except Exception:
            logger.exception(f"AZURE LAST SYNC UPDATE ERROR | client_id={client_id}")
            db.session.rollback()
            return {
                "status": "error",
                "message": "Failed updating last sync",
                "findings_created": 0
            }

        audit_elapsed = time.time() - audit_start
        logger.info(
            f"AZURE AUDIT COMPLETED SUCCESSFULLY | client_id={client_id} | "
            f"total_duration={audit_elapsed:.2f}s"
        )

        return {
            "status": "ok",
            "findings_created": findings_created,
            "duration_seconds": round(audit_elapsed, 2)
        }

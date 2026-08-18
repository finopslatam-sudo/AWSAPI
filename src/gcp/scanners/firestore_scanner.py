import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class FirestoreScanner(GCPBaseScanner):
    """Handles Firestore databases."""

    def scan_databases(self):
        try:
            firestore = self._client("firestore", "v1")

            parent = f"projects/{self.project_id}"
            response = firestore.projects().databases().list(parent=parent).execute()

            for database in response.get("databases", []):
                self.upsert_resource(
                    service_name="Firestore",
                    resource_type="Database",
                    resource_id=database["name"],
                    region=database.get("locationId"),
                    state=None,
                    tags={},
                    resource_metadata={
                        "name": database["name"].split("/")[-1],
                        "type": database.get("type"),
                        "concurrency_mode": database.get("concurrencyMode"),
                        "delete_protection_state": database.get("deleteProtectionState"),
                    }
                )

        except Exception:
            logger.exception(f"GCP Firestore scan failed | project={self.project_id}")
            raise

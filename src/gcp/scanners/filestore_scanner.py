import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class FilestoreScanner(GCPBaseScanner):
    """Handles Filestore instances (equivalente a EFS)."""

    def scan_filestore_instances(self):
        try:
            file_api = self._client("file", "v1")

            parent = f"projects/{self.project_id}/locations/-"

            for page in self._paginate(
                file_api.projects().locations().instances(), "list", parent=parent
            ):
                for instance in page.get("instances", []):
                    location = instance.get("name", "").split("/locations/")[-1].split("/instances/")[0]

                    self.upsert_resource(
                        service_name="Filestore",
                        resource_type="Instance",
                        resource_id=instance["name"],
                        region=location,
                        state=instance.get("state"),
                        tags=instance.get("labels") or {},
                        resource_metadata={
                            "name": instance["name"].split("/")[-1],
                            "tier": instance.get("tier"),
                            "file_shares": instance.get("fileShares") or [],
                        }
                    )

        except Exception:
            logger.exception(f"GCP Filestore scan failed | project={self.project_id}")
            raise

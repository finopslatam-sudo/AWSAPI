import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class LoggingScanner(GCPBaseScanner):
    """Handles Cloud Logging log buckets (equivalente a CloudWatch
    Logs en AWS / Monitor en Azure — gap real detectado en la
    comparativa multi-cloud)."""

    def scan_log_buckets(self):
        try:
            logging_api = self._client("logging", "v2")

            parent = f"projects/{self.project_id}/locations/-"

            for page in self._paginate(
                logging_api.projects().locations().buckets(), "list", parent=parent
            ):
                for bucket in page.get("buckets", []):
                    location = bucket.get("name", "").split("/locations/")[-1].split("/buckets/")[0]

                    self.upsert_resource(
                        service_name="CloudLogging",
                        resource_type="LogBucket",
                        resource_id=bucket["name"],
                        region=location,
                        state=bucket.get("lifecycleState"),
                        tags={},
                        resource_metadata={
                            "name": bucket["name"].split("/")[-1],
                            "retention_days": bucket.get("retentionDays"),
                            "locked": bucket.get("locked"),
                            "cmek_settings": bool(bucket.get("cmekSettings")),
                        }
                    )

        except Exception:
            logger.exception(f"GCP Cloud Logging scan failed | project={self.project_id}")
            raise

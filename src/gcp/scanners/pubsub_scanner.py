import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class PubSubScanner(GCPBaseScanner):
    """Handles Pub/Sub topics (equivalente a SNS/SQS de AWS)."""

    def scan_topics(self):
        try:
            pubsub = self._client("pubsub", "v1")

            project_path = f"projects/{self.project_id}"

            for page in self._paginate(
                pubsub.projects().topics(), "list", project=project_path
            ):
                for topic in page.get("topics", []):
                    self.upsert_resource(
                        service_name="PubSub",
                        resource_type="Topic",
                        resource_id=topic["name"],
                        region="global",
                        state=None,
                        tags=topic.get("labels") or {},
                        resource_metadata={
                            "name": topic["name"].split("/")[-1],
                            "kms_key_name": topic.get("kmsKeyName"),
                        }
                    )

        except Exception:
            logger.exception(f"GCP Pub/Sub scan failed | project={self.project_id}")
            raise

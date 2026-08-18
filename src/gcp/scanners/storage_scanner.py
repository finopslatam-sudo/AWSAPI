import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class StorageScanner(GCPBaseScanner):
    """Handles Cloud Storage buckets."""

    def scan_buckets(self):
        try:
            storage = self._client("storage", "v1")

            for page in self._paginate(
                storage.buckets(), "list", project=self.project_id
            ):
                for bucket in page.get("items", []):
                    iam_config = bucket.get("iamConfiguration") or {}
                    uniform_access = (
                        iam_config.get("uniformBucketLevelAccess") or {}
                    ).get("enabled")

                    self.upsert_resource(
                        service_name="CloudStorage",
                        resource_type="Bucket",
                        resource_id=bucket["selfLink"],
                        region=bucket.get("location"),
                        state=None,
                        tags=bucket.get("labels") or {},
                        resource_metadata={
                            "name": bucket.get("name"),
                            "storage_class": bucket.get("storageClass"),
                            "uniform_bucket_level_access": uniform_access,
                            "versioning_enabled": (bucket.get("versioning") or {}).get("enabled"),
                            "public_access_prevention": iam_config.get("publicAccessPrevention"),
                        }
                    )

        except Exception:
            logger.exception(f"GCP Cloud Storage scan failed | project={self.project_id}")
            raise

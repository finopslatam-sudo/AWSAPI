import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class RedisScanner(GCPBaseScanner):
    """Handles Memorystore for Redis (equivalente a ElastiCache)."""

    def scan_redis_instances(self):
        try:
            redis = self._client("redis", "v1")

            parent = f"projects/{self.project_id}/locations/-"

            for page in self._paginate(
                redis.projects().locations().instances(), "list", parent=parent
            ):
                for instance in page.get("instances", []):
                    location = instance.get("name", "").split("/locations/")[-1].split("/instances/")[0]

                    self.upsert_resource(
                        service_name="Memorystore",
                        resource_type="RedisInstance",
                        resource_id=instance["name"],
                        region=location,
                        state=instance.get("state"),
                        tags=instance.get("labels") or {},
                        resource_metadata={
                            "name": instance["name"].split("/")[-1],
                            "tier": instance.get("tier"),
                            "memory_size_gb": instance.get("memorySizeGb"),
                            "redis_version": instance.get("redisVersion"),
                            "authorized_network": instance.get("authorizedNetwork"),
                        }
                    )

        except Exception:
            logger.exception(f"GCP Memorystore scan failed | project={self.project_id}")
            raise

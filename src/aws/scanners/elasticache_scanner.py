import logging

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class ElastiCacheScanner(BaseScanner):
    """Handles ElastiCache clusters (Redis / Memcached)."""

    def scan_elasticache(self, region):
        try:
            elasticache = self.aws_session.client("elasticache", region_name=region)
            paginator = elasticache.get_paginator("describe_cache_clusters")

            for page in paginator.paginate(ShowCacheNodeInfo=True):
                for cluster in page.get("CacheClusters", []):
                    self.upsert_resource(
                        service_name="ElastiCache",
                        resource_type="CacheCluster",
                        resource_id=cluster["CacheClusterId"],
                        region=region,
                        state=cluster.get("CacheClusterStatus"),
                        tags={},
                        resource_metadata={
                            "engine": cluster.get("Engine"),
                            "node_type": cluster.get("CacheNodeType"),
                            "num_nodes": cluster.get("NumCacheNodes"),
                            "snapshot_retention_limit": cluster.get("SnapshotRetentionLimit"),
                        }
                    )

        except Exception:
            logger.exception(f"ElastiCache scan failed | region={region}")
            raise

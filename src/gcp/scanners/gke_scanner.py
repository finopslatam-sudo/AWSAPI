import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class GKEScanner(GCPBaseScanner):
    """Handles Google Kubernetes Engine (GKE) clusters."""

    def scan_clusters(self):
        try:
            container = self._client("container", "v1")

            parent = f"projects/{self.project_id}/locations/-"
            response = container.projects().locations().clusters().list(parent=parent).execute()

            for cluster in response.get("clusters", []):
                node_pools = cluster.get("nodePools") or []
                any_pool_without_autoscaling = any(
                    not (pool.get("autoscaling") or {}).get("enabled") for pool in node_pools
                )

                resource_id = cluster.get(
                    "selfLink",
                    f"projects/{self.project_id}/locations/{cluster.get('location')}/clusters/{cluster.get('name')}"
                )

                self.upsert_resource(
                    service_name="GKE",
                    resource_type="Cluster",
                    resource_id=resource_id,
                    region=cluster.get("location"),
                    state=cluster.get("status"),
                    tags=cluster.get("resourceLabels") or {},
                    resource_metadata={
                        "name": cluster.get("name"),
                        "current_node_count": cluster.get("currentNodeCount"),
                        "any_pool_without_autoscaling": any_pool_without_autoscaling,
                        "release_channel": (cluster.get("releaseChannel") or {}).get("channel"),
                    }
                )

        except Exception:
            logger.exception(f"GCP GKE scan failed | project={self.project_id}")
            raise

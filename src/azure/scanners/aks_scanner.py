import logging

from azure.mgmt.containerservice import ContainerServiceClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class AKSScanner(AzureBaseScanner):
    """Handles Azure Kubernetes Service (AKS)."""

    def scan_aks_clusters(self):
        try:
            aks_client = ContainerServiceClient(self.credential, self.subscription_id)

            for cluster in aks_client.managed_clusters.list():
                resource_group = cluster.id.split("/")[4]

                agent_pools = cluster.agent_pool_profiles or []
                any_pool_without_autoscaling = any(
                    not pool.enable_auto_scaling for pool in agent_pools
                )
                total_node_count = sum(pool.count or 0 for pool in agent_pools)

                self.upsert_resource(
                    service_name="AKS",
                    resource_type="ManagedCluster",
                    resource_id=cluster.id,
                    region=cluster.location,
                    state=cluster.provisioning_state,
                    tags=cluster.tags or {},
                    resource_metadata={
                        "name": cluster.name,
                        "resource_group": resource_group,
                        "kubernetes_version": cluster.kubernetes_version,
                        "node_resource_group": cluster.node_resource_group,
                        "disable_local_accounts": cluster.disable_local_accounts,
                        "agent_pool_count": len(agent_pools),
                        "total_node_count": total_node_count,
                        "any_pool_without_autoscaling": any_pool_without_autoscaling,
                    }
                )

        except Exception:
            logger.exception(f"Azure AKS scan failed | subscription={self.subscription_id}")
            raise

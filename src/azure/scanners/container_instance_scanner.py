import logging

from azure.mgmt.containerinstance import ContainerInstanceManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class ContainerInstanceScanner(AzureBaseScanner):
    """Handles Azure Container Instances (ACI)."""

    def scan_container_instances(self):
        try:
            aci_client = ContainerInstanceManagementClient(self.credential, self.subscription_id)

            for group in aci_client.container_groups.list():
                resource_group = group.id.split("/")[4]

                containers = group.containers or []
                total_cpu = sum(
                    (c.resources.requests.cpu if c.resources and c.resources.requests else 0) or 0
                    for c in containers
                )
                total_memory_gb = sum(
                    (c.resources.requests.memory_in_gb if c.resources and c.resources.requests else 0) or 0
                    for c in containers
                )

                self.upsert_resource(
                    service_name="ContainerInstances",
                    resource_type="ContainerGroup",
                    resource_id=group.id,
                    region=group.location,
                    state=group.provisioning_state,
                    tags=group.tags or {},
                    resource_metadata={
                        "name": group.name,
                        "resource_group": resource_group,
                        "os_type": group.os_type,
                        "restart_policy": group.restart_policy,
                        "container_count": len(containers),
                        "total_cpu": total_cpu,
                        "total_memory_gb": total_memory_gb,
                        "ip_address_type": group.ip_address.type if group.ip_address else None,
                    }
                )

        except Exception:
            logger.exception(f"Azure Container Instances scan failed | subscription={self.subscription_id}")
            raise

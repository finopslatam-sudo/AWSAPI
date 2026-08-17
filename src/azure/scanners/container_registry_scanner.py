import logging

from azure.mgmt.containerregistry import ContainerRegistryManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class ContainerRegistryScanner(AzureBaseScanner):
    """Handles Azure Container Registry (ACR)."""

    def scan_container_registries(self):
        try:
            acr_client = ContainerRegistryManagementClient(self.credential, self.subscription_id)

            for registry in acr_client.registries.list():
                resource_group = registry.id.split("/")[4]

                self.upsert_resource(
                    service_name="ContainerRegistry",
                    resource_type="Registry",
                    resource_id=registry.id,
                    region=registry.location,
                    state=registry.provisioning_state,
                    tags=registry.tags or {},
                    resource_metadata={
                        "name": registry.name,
                        "resource_group": resource_group,
                        "sku_name": registry.sku.name if registry.sku else None,
                        "admin_user_enabled": registry.admin_user_enabled,
                        "public_network_access": registry.public_network_access,
                    }
                )

        except Exception:
            logger.exception(f"Azure Container Registry scan failed | subscription={self.subscription_id}")
            raise

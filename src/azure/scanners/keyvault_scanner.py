import logging

from azure.mgmt.keyvault import KeyVaultManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class KeyVaultScanner(AzureBaseScanner):
    """Handles Azure Key Vault."""

    def scan_key_vaults(self):
        try:
            kv_client = KeyVaultManagementClient(self.credential, self.subscription_id)

            for vault in kv_client.vaults.list_by_subscription():
                resource_group = vault.id.split("/")[4]
                props = vault.properties

                network_acls = props.network_acls if props else None

                self.upsert_resource(
                    service_name="KeyVault",
                    resource_type="Vault",
                    resource_id=vault.id,
                    region=vault.location,
                    state="active",
                    tags=vault.tags or {},
                    resource_metadata={
                        "name": vault.name,
                        "resource_group": resource_group,
                        "sku_name": props.sku.name if props and props.sku else None,
                        "purge_protection_enabled": bool(props.enable_purge_protection) if props else False,
                        "soft_delete_enabled": bool(props.enable_soft_delete) if props else False,
                        "network_default_action": network_acls.default_action if network_acls else "Allow",
                    }
                )

        except Exception:
            logger.exception(f"Azure Key Vault scan failed | subscription={self.subscription_id}")
            raise

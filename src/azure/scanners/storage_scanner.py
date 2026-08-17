import logging

from azure.mgmt.storage import StorageManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class StorageScanner(AzureBaseScanner):
    """Handles Azure Storage Accounts."""

    def scan_storage_accounts(self):
        try:
            storage_client = StorageManagementClient(self.credential, self.subscription_id)

            for account in storage_client.storage_accounts.list():
                resource_group = account.id.split("/")[4]

                self.upsert_resource(
                    service_name="StorageAccounts",
                    resource_type="StorageAccount",
                    resource_id=account.id,
                    region=account.location,
                    state=account.status_of_primary.value if account.status_of_primary else None,
                    tags=account.tags or {},
                    resource_metadata={
                        "name": account.name,
                        "resource_group": resource_group,
                        "kind": account.kind.value if account.kind else None,
                        "sku_name": account.sku.name.value if account.sku and account.sku.name else None,
                        "access_tier": account.access_tier.value if account.access_tier else None,
                        "allow_blob_public_access": account.allow_blob_public_access,
                        "supports_https_traffic_only": account.enable_https_traffic_only,
                    }
                )

        except Exception:
            logger.exception(f"Azure Storage Accounts scan failed | subscription={self.subscription_id}")
            raise

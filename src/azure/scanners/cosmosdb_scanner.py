import logging

from azure.mgmt.cosmosdb import CosmosDBManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class CosmosDBScanner(AzureBaseScanner):
    """Handles Azure Cosmos DB."""

    def scan_cosmosdb_accounts(self):
        try:
            cosmos_client = CosmosDBManagementClient(self.credential, self.subscription_id)

            for account in cosmos_client.database_accounts.list():
                resource_group = account.id.split("/")[4]

                locations = account.locations or []

                self.upsert_resource(
                    service_name="CosmosDB",
                    resource_type="DatabaseAccount",
                    resource_id=account.id,
                    region=account.location,
                    state=account.provisioning_state,
                    tags=account.tags or {},
                    resource_metadata={
                        "name": account.name,
                        "resource_group": resource_group,
                        "kind": account.kind,
                        "region_count": len(locations),
                        "regions": [loc.location_name for loc in locations],
                        "public_network_access": account.public_network_access,
                        "is_virtual_network_filter_enabled": bool(account.is_virtual_network_filter_enabled),
                        "enable_free_tier": bool(account.enable_free_tier),
                    }
                )

        except Exception:
            logger.exception(f"Azure Cosmos DB scan failed | subscription={self.subscription_id}")
            raise

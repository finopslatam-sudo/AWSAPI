import logging

from azure.mgmt.postgresqlflexibleservers import PostgreSQLManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class PostgreSQLScanner(AzureBaseScanner):
    """Handles Azure Database for PostgreSQL — Flexible Server.

    Solo Flexible Server: Single Server fue retirado por Microsoft
    (marzo 2025), no tiene sentido escanear una SKU que ya no existe
    para clientes nuevos.
    """

    def scan_postgresql_servers(self):
        try:
            pg_client = PostgreSQLManagementClient(self.credential, self.subscription_id)

            for server in pg_client.servers.list():
                resource_group = server.id.split("/")[4]

                network = server.network
                backup = server.backup
                high_availability = server.high_availability
                storage = server.storage

                self.upsert_resource(
                    service_name="PostgreSQL",
                    resource_type="FlexibleServer",
                    resource_id=server.id,
                    region=server.location,
                    state=server.state,
                    tags=server.tags or {},
                    resource_metadata={
                        "name": server.name,
                        "resource_group": resource_group,
                        "sku_name": server.sku.name if server.sku else None,
                        "sku_tier": server.sku.tier if server.sku else None,
                        "version": server.version,
                        "storage_size_gb": storage.storage_size_gb if storage else None,
                        "backup_retention_days": backup.backup_retention_days if backup else None,
                        "public_network_access": network.public_network_access if network else None,
                        "high_availability_mode": high_availability.mode if high_availability else None,
                    }
                )

        except Exception:
            logger.exception(f"Azure PostgreSQL scan failed | subscription={self.subscription_id}")
            raise

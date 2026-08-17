import logging

from azure.mgmt.sql import SqlManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class SQLScanner(AzureBaseScanner):
    """Handles Azure SQL Database: logical servers + databases."""

    def scan_sql_databases(self):
        try:
            sql_client = SqlManagementClient(self.credential, self.subscription_id)

            for server in sql_client.servers.list():
                resource_group = server.id.split("/")[4]

                self.upsert_resource(
                    service_name="SQLDatabase",
                    resource_type="SqlServer",
                    resource_id=server.id,
                    region=server.location,
                    state=server.state,
                    tags=server.tags or {},
                    resource_metadata={
                        "name": server.name,
                        "resource_group": resource_group,
                        "public_network_access": server.public_network_access.value if server.public_network_access else None,
                        "minimal_tls_version": server.minimal_tls_version,
                        "version": server.version,
                    }
                )

                self._scan_databases_in_server(sql_client, resource_group, server)

        except Exception:
            logger.exception(f"Azure SQL scan failed | subscription={self.subscription_id}")
            raise

    # ------------------------------------------------------------------
    def _scan_databases_in_server(self, sql_client, resource_group, server):
        for database in sql_client.databases.list_by_server(resource_group, server.name):
            # "master" es la base de sistema, no es un recurso facturable
            # relevante para FinOps — se omite igual que se omiten
            # recursos de sistema en otros scanners.
            if database.name == "master":
                continue

            self.upsert_resource(
                service_name="SQLDatabase",
                resource_type="SqlDatabase",
                resource_id=database.id,
                region=database.location,
                state=database.status.value if database.status else None,
                tags=database.tags or {},
                resource_metadata={
                    "name": database.name,
                    "server_name": server.name,
                    "sku_name": database.sku.name if database.sku else None,
                    "sku_tier": database.sku.tier if database.sku else None,
                    "max_size_bytes": database.max_size_bytes,
                }
            )

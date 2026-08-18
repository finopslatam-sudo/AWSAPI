import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class SQLScanner(GCPBaseScanner):
    """Handles Cloud SQL (instancias Postgres/MySQL/SQL Server, todas
    bajo un único recurso `instances` de la API sqladmin — a diferencia
    de Azure, que separa SQL Database/PostgreSQL/MySQL en 3 APIs)."""

    def scan_sql_instances(self):
        try:
            sqladmin = self._client("sqladmin", "v1beta4")

            for page in self._paginate(
                sqladmin.instances(), "list", project=self.project_id
            ):
                for instance in page.get("items", []):
                    settings = instance.get("settings") or {}
                    ip_config = settings.get("ipConfiguration") or {}
                    backup_config = settings.get("backupConfiguration") or {}

                    self.upsert_resource(
                        service_name="CloudSQL",
                        resource_type="DatabaseInstance",
                        resource_id=instance["selfLink"],
                        region=instance.get("region"),
                        state=instance.get("state"),
                        tags={},
                        resource_metadata={
                            "name": instance.get("name"),
                            "database_version": instance.get("databaseVersion"),
                            "tier": settings.get("tier"),
                            "require_ssl": ip_config.get("requireSsl"),
                            "authorized_networks": ip_config.get("authorizedNetworks") or [],
                            "backup_enabled": backup_config.get("enabled"),
                        }
                    )

        except Exception:
            logger.exception(f"GCP Cloud SQL scan failed | project={self.project_id}")
            raise

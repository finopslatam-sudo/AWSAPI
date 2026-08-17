import logging

from azure.mgmt.web import WebSiteManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class AppServiceScanner(AzureBaseScanner):
    """Handles Azure App Service (Web Apps).

    Excluye explícitamente los sites con kind "functionapp": en Azure,
    Functions también vive bajo Microsoft.Web/sites, pero es un
    servicio distinto (Azure Functions, próximo en la lista de
    prioridad) — evita contar el mismo recurso dos veces.
    """

    def scan_app_services(self):
        try:
            web_client = WebSiteManagementClient(self.credential, self.subscription_id)

            for site in web_client.web_apps.list():
                kind = (site.kind or "").lower()
                if "functionapp" in kind:
                    continue

                resource_group = site.id.split("/")[4]

                self.upsert_resource(
                    service_name="AppService",
                    resource_type="WebApp",
                    resource_id=site.id,
                    region=site.location,
                    state=site.state,
                    tags=site.tags or {},
                    resource_metadata={
                        "name": site.name,
                        "resource_group": resource_group,
                        "kind": site.kind,
                        "https_only": site.https_only,
                        "default_host_name": site.default_host_name,
                        "server_farm_id": site.server_farm_id,
                    }
                )

        except Exception:
            logger.exception(f"Azure App Service scan failed | subscription={self.subscription_id}")
            raise

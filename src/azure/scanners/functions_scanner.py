import logging

from azure.mgmt.web import WebSiteManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class FunctionsScanner(AzureBaseScanner):
    """Handles Azure Functions.

    Azure Functions vive bajo el mismo recurso que App Service
    (Microsoft.Web/sites) — se distingue por `kind` conteniendo
    "functionapp". AppServiceScanner ya excluye estos sites de su
    propio scan, así que no hay doble conteo entre ambos servicios.
    """

    def scan_functions(self):
        try:
            web_client = WebSiteManagementClient(self.credential, self.subscription_id)

            for site in web_client.web_apps.list():
                kind = (site.kind or "").lower()
                if "functionapp" not in kind:
                    continue

                resource_group = site.id.split("/")[4]

                self.upsert_resource(
                    service_name="Functions",
                    resource_type="FunctionApp",
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
            logger.exception(f"Azure Functions scan failed | subscription={self.subscription_id}")
            raise

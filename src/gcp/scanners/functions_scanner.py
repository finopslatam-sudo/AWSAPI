import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class FunctionsScanner(GCPBaseScanner):
    """Handles Cloud Functions (2nd gen, corre sobre Cloud Run por
    debajo, pero se reporta como servicio propio igual que en AWS/Azure
    con Lambda/Functions separados de EC2/App Service)."""

    def scan_functions(self):
        try:
            functions = self._client("cloudfunctions", "v2")

            parent = f"projects/{self.project_id}/locations/-"
            response = functions.projects().locations().functions().list(parent=parent).execute()

            for fn in response.get("functions", []):
                location = fn.get("name", "").split("/locations/")[-1].split("/functions/")[0]

                build_config = fn.get("buildConfig") or {}
                service_config = fn.get("serviceConfig") or {}

                self.upsert_resource(
                    service_name="CloudFunctions",
                    resource_type="Function",
                    resource_id=fn["name"],
                    region=location,
                    state=fn.get("state"),
                    tags=fn.get("labels") or {},
                    resource_metadata={
                        "runtime": build_config.get("runtime"),
                        "environment": fn.get("environment"),
                        "ingress_settings": service_config.get("ingressSettings"),
                        "available_memory": service_config.get("availableMemory"),
                        "max_instance_count": service_config.get("maxInstanceCount"),
                    }
                )

        except Exception:
            logger.exception(f"GCP Cloud Functions scan failed | project={self.project_id}")
            raise

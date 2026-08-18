import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class RunScanner(GCPBaseScanner):
    """Handles Cloud Run services."""

    def scan_services(self):
        try:
            run = self._client("run", "v2")

            parent = f"projects/{self.project_id}/locations/-"
            response = run.projects().locations().services().list(parent=parent).execute()

            for service in response.get("services", []):
                # name: projects/{project}/locations/{location}/services/{service}
                location = service.get("name", "").split("/locations/")[-1].split("/services/")[0]

                template = service.get("template") or {}
                containers = template.get("containers") or []
                ingress = service.get("ingress")

                self.upsert_resource(
                    service_name="CloudRun",
                    resource_type="Service",
                    resource_id=service["name"],
                    region=location,
                    state=None,
                    tags=service.get("labels") or {},
                    resource_metadata={
                        "uri": service.get("uri"),
                        "ingress": ingress,
                        "container_count": len(containers),
                        "max_instance_count": (template.get("scaling") or {}).get("maxInstanceCount"),
                    }
                )

        except Exception:
            logger.exception(f"GCP Cloud Run scan failed | project={self.project_id}")
            raise

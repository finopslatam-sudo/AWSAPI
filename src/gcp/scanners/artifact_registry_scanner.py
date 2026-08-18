import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class ArtifactRegistryScanner(GCPBaseScanner):
    """Handles Artifact Registry (equivalente a ECR/ACR)."""

    def scan_repositories(self):
        try:
            artifact_registry = self._client("artifactregistry", "v1")

            parent = f"projects/{self.project_id}/locations/-"

            for page in self._paginate(
                artifact_registry.projects().locations().repositories(),
                "list",
                parent=parent
            ):
                for repo in page.get("repositories", []):
                    location = repo.get("name", "").split("/locations/")[-1].split("/repositories/")[0]

                    self.upsert_resource(
                        service_name="ArtifactRegistry",
                        resource_type="Repository",
                        resource_id=repo["name"],
                        region=location,
                        state=None,
                        tags=repo.get("labels") or {},
                        resource_metadata={
                            "format": repo.get("format"),
                            "mode": repo.get("mode"),
                            "size_bytes": repo.get("sizeBytes"),
                        }
                    )

        except Exception:
            logger.exception(f"GCP Artifact Registry scan failed | project={self.project_id}")
            raise

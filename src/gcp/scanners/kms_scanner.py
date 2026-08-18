import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class KMSScanner(GCPBaseScanner):
    """Handles Cloud KMS key rings. A diferencia de la mayoría de APIs
    de GCP, keyRings no tiene un list global: hay que iterar location
    por location (equivalente conceptual a KMS por región en AWS)."""

    def scan_key_rings(self):
        try:
            kms = self._client("cloudkms", "v1")

            locations_resp = kms.projects().locations().list(
                name=f"projects/{self.project_id}"
            ).execute()

            for location in locations_resp.get("locations", []):
                location_id = location.get("locationId")
                parent = f"projects/{self.project_id}/locations/{location_id}"

                for page in self._paginate(
                    kms.projects().locations().keyRings(), "list", parent=parent
                ):
                    for key_ring in page.get("keyRings", []):
                        self.upsert_resource(
                            service_name="CloudKMS",
                            resource_type="KeyRing",
                            resource_id=key_ring["name"],
                            region=location_id,
                            state=None,
                            tags={},
                            resource_metadata={
                                "name": key_ring["name"].split("/")[-1],
                                "create_time": key_ring.get("createTime"),
                            }
                        )

        except Exception:
            logger.exception(f"GCP Cloud KMS scan failed | project={self.project_id}")
            raise

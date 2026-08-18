import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class SnapshotScanner(GCPBaseScanner):
    """Handles Compute Engine Disk Snapshots (equivalente a EBS
    Snapshots en AWS/Managed Disk Snapshots en Azure — recurso global,
    no está atado a una zona)."""

    def scan_snapshots(self):
        try:
            compute = self._client("compute", "v1")

            for page in self._paginate(
                compute.snapshots(), "list", project=self.project_id
            ):
                for snapshot in page.get("items", []):
                    self.upsert_resource(
                        service_name="Snapshots",
                        resource_type="Snapshot",
                        resource_id=snapshot["selfLink"],
                        region="global",
                        state=snapshot.get("status"),
                        tags=snapshot.get("labels") or {},
                        resource_metadata={
                            "name": snapshot.get("name"),
                            "source_disk": snapshot.get("sourceDisk"),
                            "disk_size_gb": snapshot.get("diskSizeGb"),
                        }
                    )

        except Exception:
            logger.exception(f"GCP Snapshots scan failed | project={self.project_id}")
            raise

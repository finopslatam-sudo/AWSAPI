import logging

from azure.mgmt.compute import ComputeManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class SnapshotScanner(AzureBaseScanner):
    """Handles Azure Managed Disk Snapshots (equivalente a EBS
    Snapshots en AWS — clásico artefacto "zombie" cuando el disco de
    origen ya fue eliminado pero el snapshot sigue facturando)."""

    def scan_snapshots(self):
        try:
            compute_client = ComputeManagementClient(self.credential, self.subscription_id)

            for snapshot in compute_client.snapshots.list():
                resource_group = snapshot.id.split("/")[4]

                creation_data = snapshot.creation_data
                source_resource_id = (
                    creation_data.source_resource_id if creation_data else None
                )

                self.upsert_resource(
                    service_name="Snapshots",
                    resource_type="Snapshot",
                    resource_id=snapshot.id,
                    region=snapshot.location,
                    state=getattr(snapshot, "provisioning_state", None),
                    tags=snapshot.tags or {},
                    resource_metadata={
                        "name": snapshot.name,
                        "resource_group": resource_group,
                        "source_resource_id": source_resource_id,
                        "disk_size_gb": getattr(snapshot, "disk_size_gb", None),
                    }
                )

        except Exception:
            logger.exception(f"Azure Snapshots scan failed | subscription={self.subscription_id}")
            raise

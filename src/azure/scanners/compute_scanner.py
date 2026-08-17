import logging

from azure.mgmt.compute import ComputeManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class ComputeScanner(AzureBaseScanner):
    """Handles Azure Virtual Machines y Managed Disks (ambos bajo
    ComputeManagementClient, mismo patrón que EC2+EBS en AWS)."""

    def scan_virtual_machines(self):
        try:
            compute_client = ComputeManagementClient(self.credential, self.subscription_id)

            for vm in compute_client.virtual_machines.list_all():
                # El resource group siempre va en la posición 4 de un
                # Resource ID de ARM: /subscriptions/{sub}/resourceGroups/{rg}/...
                resource_group = vm.id.split("/")[4]

                power_state = self._get_power_state(compute_client, resource_group, vm.name)

                os_type = None
                if vm.storage_profile and vm.storage_profile.os_disk and vm.storage_profile.os_disk.os_type:
                    os_type = vm.storage_profile.os_disk.os_type.value

                self.upsert_resource(
                    service_name="VirtualMachines",
                    resource_type="VirtualMachine",
                    resource_id=vm.id,
                    region=vm.location,
                    state=power_state,
                    tags=vm.tags or {},
                    resource_metadata={
                        "name": vm.name,
                        "resource_group": resource_group,
                        "vm_size": vm.hardware_profile.vm_size if vm.hardware_profile else None,
                        "os_type": os_type,
                    }
                )

        except Exception:
            logger.exception(f"Azure VM scan failed | subscription={self.subscription_id}")
            raise

    # ------------------------------------------------------------------
    # POWER STATE (requiere una llamada aparte a instance_view, a
    # diferencia de AWS donde el estado viene en describe_instances)
    # ------------------------------------------------------------------
    def _get_power_state(self, compute_client, resource_group, vm_name):
        try:
            instance_view = compute_client.virtual_machines.instance_view(
                resource_group, vm_name
            )
            for status in instance_view.statuses:
                if status.code.startswith("PowerState/"):
                    return status.code.split("/")[-1]
            return None
        except Exception:
            logger.warning(f"No se pudo obtener power state | vm={vm_name}")
            return None

    # ------------------------------------------------------------------
    # MANAGED DISKS
    # ------------------------------------------------------------------
    def scan_managed_disks(self):
        try:
            compute_client = ComputeManagementClient(self.credential, self.subscription_id)

            for disk in compute_client.disks.list():
                resource_group = disk.id.split("/")[4]

                self.upsert_resource(
                    service_name="ManagedDisks",
                    resource_type="Disk",
                    resource_id=disk.id,
                    region=disk.location,
                    state=disk.disk_state,
                    tags=disk.tags or {},
                    resource_metadata={
                        "name": disk.name,
                        "resource_group": resource_group,
                        "sku_name": disk.sku.name if disk.sku else None,
                        "disk_size_gb": disk.disk_size_gb,
                        "managed_by": disk.managed_by,
                    }
                )

        except Exception:
            logger.exception(f"Azure Managed Disks scan failed | subscription={self.subscription_id}")
            raise

import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class ComputeScanner(GCPBaseScanner):
    """Handles Compute Engine (VM instances), Persistent Disks y Static
    IP Addresses — los 3 bajo la API `compute` v1, mismo patrón que
    EC2+EBS+EIP en AWS / VMs+Managed Disks en Azure."""

    def scan_instances(self):
        try:
            compute = self._client("compute", "v1")

            for page in self._paginate(
                compute.instances(), "aggregatedList", project=self.project_id
            ):
                for zone, scoped_list in (page.get("items") or {}).items():
                    for instance in scoped_list.get("instances", []):
                        zone_name = zone.split("/")[-1]
                        machine_type = (instance.get("machineType") or "").split("/")[-1]

                        self.upsert_resource(
                            service_name="ComputeEngine",
                            resource_type="Instance",
                            resource_id=instance["selfLink"],
                            region=zone_name,
                            state=instance.get("status"),
                            tags=instance.get("labels") or {},
                            resource_metadata={
                                "name": instance.get("name"),
                                "machine_type": machine_type,
                                "creation_timestamp": instance.get("creationTimestamp"),
                            }
                        )

        except Exception:
            logger.exception(f"GCP Compute Engine scan failed | project={self.project_id}")
            raise

    # ------------------------------------------------------------------
    # PERSISTENT DISKS
    # ------------------------------------------------------------------
    def scan_disks(self):
        try:
            compute = self._client("compute", "v1")

            for page in self._paginate(
                compute.disks(), "aggregatedList", project=self.project_id
            ):
                for zone, scoped_list in (page.get("items") or {}).items():
                    for disk in scoped_list.get("disks", []):
                        zone_name = zone.split("/")[-1]

                        self.upsert_resource(
                            service_name="PersistentDisks",
                            resource_type="Disk",
                            resource_id=disk["selfLink"],
                            region=zone_name,
                            state=disk.get("status"),
                            tags=disk.get("labels") or {},
                            resource_metadata={
                                "name": disk.get("name"),
                                "size_gb": disk.get("sizeGb"),
                                "type": (disk.get("type") or "").split("/")[-1],
                                "users": disk.get("users") or [],
                            }
                        )

        except Exception:
            logger.exception(f"GCP Persistent Disks scan failed | project={self.project_id}")
            raise

    # ------------------------------------------------------------------
    # STATIC IP ADDRESSES (regionales — las globales son menos comunes
    # en cargas FinOps típicas y se dejan fuera de la fase base)
    # ------------------------------------------------------------------
    def scan_addresses(self):
        try:
            compute = self._client("compute", "v1")

            for page in self._paginate(
                compute.addresses(), "aggregatedList", project=self.project_id
            ):
                for region, scoped_list in (page.get("items") or {}).items():
                    for address in scoped_list.get("addresses", []):
                        region_name = region.split("/")[-1]

                        self.upsert_resource(
                            service_name="StaticIPs",
                            resource_type="Address",
                            resource_id=address["selfLink"],
                            region=region_name,
                            state=address.get("status"),
                            tags=address.get("labels") or {},
                            resource_metadata={
                                "name": address.get("name"),
                                "address": address.get("address"),
                                "address_type": address.get("addressType"),
                                "users": address.get("users") or [],
                            }
                        )

        except Exception:
            logger.exception(f"GCP Static IPs scan failed | project={self.project_id}")
            raise

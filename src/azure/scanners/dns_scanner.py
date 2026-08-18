import logging

from azure.mgmt.dns import DnsManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class DNSScanner(AzureBaseScanner):
    """Handles Azure DNS zones (equivalente a Route53 en AWS — gap
    real detectado en la comparativa multi-cloud)."""

    def scan_dns_zones(self):
        try:
            dns_client = DnsManagementClient(self.credential, self.subscription_id)

            for zone in dns_client.zones.list():
                resource_group = zone.id.split("/")[4]

                self.upsert_resource(
                    service_name="DNS",
                    resource_type="Zone",
                    resource_id=zone.id,
                    region=zone.location,
                    state=None,
                    tags=zone.tags or {},
                    resource_metadata={
                        "name": zone.name,
                        "resource_group": resource_group,
                        "zone_type": zone.zone_type,
                        "number_of_record_sets": zone.number_of_record_sets,
                    }
                )

        except Exception:
            logger.exception(f"Azure DNS scan failed | subscription={self.subscription_id}")
            raise

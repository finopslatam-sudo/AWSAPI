import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class DNSScanner(GCPBaseScanner):
    """Handles Cloud DNS managed zones (equivalente a Route53)."""

    def scan_managed_zones(self):
        try:
            dns = self._client("dns", "v1")

            for page in self._paginate(
                dns.managedZones(), "list", project=self.project_id
            ):
                for zone in page.get("managedZones", []):
                    dnssec_state = (zone.get("dnssecConfig") or {}).get("state")

                    self.upsert_resource(
                        service_name="CloudDNS",
                        resource_type="ManagedZone",
                        resource_id=zone.get("id", zone.get("name")),
                        region="global",
                        state=None,
                        tags=zone.get("labels") or {},
                        resource_metadata={
                            "name": zone.get("name"),
                            "dns_name": zone.get("dnsName"),
                            "visibility": zone.get("visibility"),
                            "dnssec_state": dnssec_state,
                        }
                    )

        except Exception:
            logger.exception(f"GCP Cloud DNS scan failed | project={self.project_id}")
            raise

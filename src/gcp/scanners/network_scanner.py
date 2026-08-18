import logging

from src.gcp.scanners.shared import GCPBaseScanner


logger = logging.getLogger(__name__)


class NetworkScanner(GCPBaseScanner):
    """Handles VPC Networks, Firewall Rules, Cloud Load Balancing
    (forwarding rules), Cloud NAT (routers) y Cloud CDN (backend
    services con CDN habilitado) — los 5 bajo la API `compute` v1,
    mismo patrón de consolidación que VNet+LB+AppGW+NAT+Firewall en el
    network_scanner.py de Azure."""

    def scan_networks(self):
        try:
            compute = self._client("compute", "v1")

            for page in self._paginate(
                compute.networks(), "list", project=self.project_id
            ):
                for network in page.get("items", []):
                    self.upsert_resource(
                        service_name="VPCNetworks",
                        resource_type="Network",
                        resource_id=network["selfLink"],
                        region="global",
                        state=None,
                        tags={},
                        resource_metadata={
                            "name": network.get("name"),
                            "auto_create_subnetworks": network.get("autoCreateSubnetworks"),
                            "subnetworks": network.get("subnetworks") or [],
                        }
                    )

        except Exception:
            logger.exception(f"GCP VPC Networks scan failed | project={self.project_id}")
            raise

    # ------------------------------------------------------------------
    # FIREWALL RULES
    # ------------------------------------------------------------------
    def scan_firewalls(self):
        try:
            compute = self._client("compute", "v1")

            for page in self._paginate(
                compute.firewalls(), "list", project=self.project_id
            ):
                for fw in page.get("items", []):
                    self.upsert_resource(
                        service_name="FirewallRules",
                        resource_type="Firewall",
                        resource_id=fw["selfLink"],
                        region="global",
                        state="enabled" if not fw.get("disabled") else "disabled",
                        tags={},
                        resource_metadata={
                            "name": fw.get("name"),
                            "direction": fw.get("direction"),
                            "source_ranges": fw.get("sourceRanges") or [],
                            "allowed": fw.get("allowed") or [],
                            "network": (fw.get("network") or "").split("/")[-1],
                        }
                    )

        except Exception:
            logger.exception(f"GCP Firewall Rules scan failed | project={self.project_id}")
            raise

    # ------------------------------------------------------------------
    # LOAD BALANCING (forwarding rules regionales — cubren la mayoría
    # de balanceadores internos/regionales; los globales quedan para
    # una iteración futura si se detecta uso real)
    # ------------------------------------------------------------------
    def scan_load_balancers(self):
        try:
            compute = self._client("compute", "v1")

            for page in self._paginate(
                compute.forwardingRules(), "aggregatedList", project=self.project_id
            ):
                for region, scoped_list in (page.get("items") or {}).items():
                    for rule in scoped_list.get("forwardingRules", []):
                        region_name = region.split("/")[-1]

                        self.upsert_resource(
                            service_name="LoadBalancing",
                            resource_type="ForwardingRule",
                            resource_id=rule["selfLink"],
                            region=region_name,
                            state=None,
                            tags={},
                            resource_metadata={
                                "name": rule.get("name"),
                                "ip_address": rule.get("IPAddress"),
                                "load_balancing_scheme": rule.get("loadBalancingScheme"),
                                "target": rule.get("target"),
                                "backend_service": rule.get("backendService"),
                            }
                        )

        except Exception:
            logger.exception(f"GCP Load Balancing scan failed | project={self.project_id}")
            raise

    # ------------------------------------------------------------------
    # CLOUD NAT (config anidada dentro de cada Cloud Router)
    # ------------------------------------------------------------------
    def scan_nat_gateways(self):
        try:
            compute = self._client("compute", "v1")

            for page in self._paginate(
                compute.routers(), "aggregatedList", project=self.project_id
            ):
                for region, scoped_list in (page.get("items") or {}).items():
                    for router in scoped_list.get("routers", []):
                        region_name = region.split("/")[-1]

                        for nat in router.get("nats", []):
                            self.upsert_resource(
                                service_name="CloudNAT",
                                resource_type="NatGateway",
                                resource_id=f"{router['selfLink']}/nats/{nat.get('name')}",
                                region=region_name,
                                state=None,
                                tags={},
                                resource_metadata={
                                    "name": nat.get("name"),
                                    "router": router.get("name"),
                                    "nat_ip_allocate_option": nat.get("natIpAllocateOption"),
                                    "nat_ips": nat.get("natIps") or [],
                                    "source_subnetwork_ip_ranges_to_nat": nat.get(
                                        "sourceSubnetworkIpRangesToNat"
                                    ),
                                }
                            )

        except Exception:
            logger.exception(f"GCP Cloud NAT scan failed | project={self.project_id}")
            raise

    # ------------------------------------------------------------------
    # CLOUD CDN (backend services globales con CDN habilitado —
    # equivalente a CloudFront en AWS, gap real detectado en la
    # comparativa multi-cloud)
    # ------------------------------------------------------------------
    def scan_cdn_backend_services(self):
        try:
            compute = self._client("compute", "v1")

            for page in self._paginate(
                compute.backendServices(), "list", project=self.project_id
            ):
                for backend_service in page.get("items", []):
                    if not backend_service.get("enableCDN"):
                        continue

                    cdn_policy = backend_service.get("cdnPolicy") or {}

                    self.upsert_resource(
                        service_name="CloudCDN",
                        resource_type="BackendService",
                        resource_id=backend_service["selfLink"],
                        region="global",
                        state=None,
                        tags={},
                        resource_metadata={
                            "name": backend_service.get("name"),
                            "backend_count": len(backend_service.get("backends") or []),
                            "cache_mode": cdn_policy.get("cacheMode"),
                        }
                    )

        except Exception:
            logger.exception(f"GCP Cloud CDN scan failed | project={self.project_id}")
            raise

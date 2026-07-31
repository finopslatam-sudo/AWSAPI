import logging

from src.aws.scanners.shared import BaseScanner


logger = logging.getLogger(__name__)


class CloudFrontScanner(BaseScanner):
    """Handles CloudFront distributions (global service) and Route53 hosted zones (global)."""

    # ------------------------------------------------------------------
    # CLOUDFRONT (GLOBAL SERVICE)
    # ------------------------------------------------------------------
    def scan_cloudfront(self):
        try:
            cloudfront = self.aws_session.client("cloudfront", region_name="us-east-1")
            paginator = cloudfront.get_paginator("list_distributions")

            for page in paginator.paginate():
                items = page.get("DistributionList", {}).get("Items", [])
                for distribution in items:
                    self.upsert_resource(
                        service_name="CloudFront",
                        resource_type="Distribution",
                        resource_id=distribution["Id"],
                        region="global",
                        state=distribution.get("Status"),
                        tags={},
                        resource_metadata={
                            "domain_name": distribution.get("DomainName"),
                            "enabled": distribution.get("Enabled"),
                            "price_class": distribution.get("PriceClass"),
                        }
                    )

        except Exception:
            logger.exception("CloudFront scan failed")
            raise

    # ------------------------------------------------------------------
    # ROUTE53 (GLOBAL SERVICE)
    # ------------------------------------------------------------------
    def scan_route53(self):
        try:
            route53 = self.aws_session.client("route53", region_name="us-east-1")
            paginator = route53.get_paginator("list_hosted_zones")

            for page in paginator.paginate():
                for zone in page.get("HostedZones", []):
                    zone_id = zone["Id"].replace("/hostedzone/", "")

                    self.upsert_resource(
                        service_name="Route53",
                        resource_type="HostedZone",
                        resource_id=zone_id,
                        region="global",
                        state="active",
                        tags={},
                        resource_metadata={
                            "name": zone.get("Name"),
                            "private_zone": zone.get("Config", {}).get("PrivateZone"),
                            "record_set_count": zone.get("ResourceRecordSetCount"),
                        }
                    )

        except Exception:
            logger.exception("Route53 scan failed")
            raise

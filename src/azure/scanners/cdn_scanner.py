import logging

from azure.mgmt.cdn import CdnManagementClient

from src.azure.scanners.shared import AzureBaseScanner


logger = logging.getLogger(__name__)


class CDNScanner(AzureBaseScanner):
    """Handles Azure CDN / Front Door profiles (equivalente a
    CloudFront en AWS — gap real detectado en la comparativa
    multi-cloud, AWS lo cubría y Azure no)."""

    def scan_cdn_profiles(self):
        try:
            cdn_client = CdnManagementClient(self.credential, self.subscription_id)

            for profile in cdn_client.profiles.list():
                resource_group = profile.id.split("/")[4]

                endpoints = list(
                    cdn_client.endpoints.list_by_profile(resource_group, profile.name)
                )
                any_http_allowed = any(
                    getattr(e, "is_http_allowed", False) for e in endpoints
                )

                self.upsert_resource(
                    service_name="CDN",
                    resource_type="Profile",
                    resource_id=profile.id,
                    region=profile.location,
                    state=getattr(profile, "resource_state", None),
                    tags=profile.tags or {},
                    resource_metadata={
                        "name": profile.name,
                        "resource_group": resource_group,
                        "sku_name": profile.sku.name if profile.sku else None,
                        "endpoint_count": len(endpoints),
                        "any_http_allowed": any_http_allowed,
                    }
                )

        except Exception:
            logger.exception(f"Azure CDN scan failed | subscription={self.subscription_id}")
            raise

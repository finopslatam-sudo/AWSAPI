from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class CDNRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += CDNRules.no_backends_rule(client_id)
        total += CDNRules.cache_mode_review_rule(client_id)
        return total

    @staticmethod
    def no_backends_rule(client_id: int):
        return CDNRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('backend_count', 0) == 0,
            finding_type="CDNBACKEND_NO_BACKENDS",
            severity="MEDIUM",
            message="Backend service con Cloud CDN habilitado pero sin ningun backend asociado; revisar si sigue en uso.",
            savings=10.0,
        )


    @staticmethod
    def cache_mode_review_rule(client_id: int):
        return CDNRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('cache_mode') == 'USE_ORIGIN_HEADERS',
            finding_type="CDNBACKEND_CACHE_MODE_REVIEW",
            severity="LOW",
            message="Backend service usa el modo de cache basado solo en headers de origen; revisar si un modo mas agresivo reduciria el trafico al origen.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudCDN",
            resource_type="BackendService",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:

            existing = GCPFinding.query.filter_by(
                client_id=client_id,
                resource_id=resource.resource_id,
                finding_type=finding_type
            ).first()

            if condition(resource):

                if existing:
                    existing.resolved = False
                    existing.message = message
                    existing.severity = severity
                    existing.estimated_monthly_savings = savings
                else:
                    created = GCPFinding.upsert_finding(
                        client_id=client_id,
                        gcp_account_id=resource.gcp_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        gcp_service="CloudCDN",
                        finding_type=finding_type,
                        severity=severity,
                        message=message,
                        estimated_monthly_savings=savings
                    )
                    if created:
                        findings_created += 1

            else:
                if existing and not existing.resolved:
                    existing.resolved = True

        return findings_created

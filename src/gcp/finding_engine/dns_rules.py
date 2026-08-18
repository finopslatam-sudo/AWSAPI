from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class DNSRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += DNSRules.dnssec_disabled_rule(client_id)
        total += DNSRules.public_zone_review_rule(client_id)
        return total

    @staticmethod
    def dnssec_disabled_rule(client_id: int):
        return DNSRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('dnssec_state') != 'on',
            finding_type="DNS_DNSSEC_DISABLED",
            severity="MEDIUM",
            message="Zona Cloud DNS sin DNSSEC habilitado; expuesta a ataques de spoofing/cache poisoning.",
            savings=0.0,
        )


    @staticmethod
    def public_zone_review_rule(client_id: int):
        return DNSRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('visibility') == 'public',
            finding_type="DNS_PUBLIC_ZONE_REVIEW",
            severity="LOW",
            message="Zona Cloud DNS publica; confirmar que la exposicion es intencional.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudDNS",
            resource_type="ManagedZone",
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
                        gcp_service="CloudDNS",
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

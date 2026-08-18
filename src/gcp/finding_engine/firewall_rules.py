from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class FirewallRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += FirewallRules.open_to_internet_rule(client_id)
        total += FirewallRules.disabled_review_rule(client_id)
        return total

    @staticmethod
    def open_to_internet_rule(client_id: int):
        return FirewallRules._evaluate_rule(
            client_id,
            condition=lambda r: '0.0.0.0/0' in ((r.resource_metadata or {}).get('source_ranges') or []) and (r.resource_metadata or {}).get('direction') == 'INGRESS',
            finding_type="FIREWALL_OPEN_TO_INTERNET",
            severity="HIGH",
            message="Regla de firewall permite ingreso desde 0.0.0.0/0 (Internet); revisar si el acceso deberia estar restringido.",
            savings=0.0,
        )


    @staticmethod
    def disabled_review_rule(client_id: int):
        return FirewallRules._evaluate_rule(
            client_id,
            condition=lambda r: r.state == 'disabled',
            finding_type="FIREWALL_DISABLED_REVIEW",
            severity="LOW",
            message="Regla de firewall deshabilitada; si ya no es necesaria, eliminarla reduce ruido de gobernanza.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="FirewallRules",
            resource_type="Firewall",
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
                        gcp_service="FirewallRules",
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

from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class NATGatewayRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += NATGatewayRules.no_nat_ips_rule(client_id)
        total += NATGatewayRules.all_subnets_rule(client_id)
        return total

    @staticmethod
    def no_nat_ips_rule(client_id: int):
        return NATGatewayRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('nat_ip_allocate_option') == 'MANUAL_ONLY' and not (r.resource_metadata or {}).get('nat_ips'),
            finding_type="NATGATEWAY_NO_NAT_IPS",
            severity="HIGH",
            message="Cloud NAT configurado con asignacion manual de IPs pero sin IPs asignadas; el trafico saliente puede estar fallando.",
            savings=32.0,
        )


    @staticmethod
    def all_subnets_rule(client_id: int):
        return NATGatewayRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('source_subnetwork_ip_ranges_to_nat') == 'ALL_SUBNETWORKS_ALL_IP_RANGES',
            finding_type="NATGATEWAY_ALL_SUBNETS",
            severity="MEDIUM",
            message="Cloud NAT aplica a todas las subredes e IPs del router; revisar si el alcance deberia ser mas acotado.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudNAT",
            resource_type="NatGateway",
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
                        gcp_service="CloudNAT",
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

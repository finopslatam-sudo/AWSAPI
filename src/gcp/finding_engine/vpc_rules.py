from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class VPCRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += VPCRules.auto_subnets_rule(client_id)
        total += VPCRules.no_subnets_rule(client_id)
        return total

    @staticmethod
    def auto_subnets_rule(client_id: int):
        return VPCRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('auto_create_subnetworks') is True,
            finding_type="VNET_AUTO_SUBNETS_ENABLED",
            severity="MEDIUM",
            message="VPC en modo auto crea subredes en todas las regiones automaticamente; revisar si se necesita un diseno mas controlado (modo custom).",
            savings=0.0,
        )


    @staticmethod
    def no_subnets_rule(client_id: int):
        return VPCRules._evaluate_rule(
            client_id,
            condition=lambda r: not (r.resource_metadata or {}).get('subnetworks'),
            finding_type="VNET_NO_SUBNETS",
            severity="LOW",
            message="VPC sin subredes creadas; probablemente sin uso real.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="VPCNetworks",
            resource_type="Network",
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
                        gcp_service="VPCNetworks",
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

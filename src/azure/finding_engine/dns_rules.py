from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class DNSRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += DNSRules.empty_zone_rule(client_id)
        total += DNSRules.private_zone_review_rule(client_id)
        return total

    @staticmethod
    def empty_zone_rule(client_id: int):
        return DNSRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('number_of_record_sets', 0) <= 2,
            finding_type="DNS_ZONE_EMPTY",
            severity="LOW",
            message="Zona DNS sin registros propios (solo NS+SOA); revisar si sigue siendo necesaria, cada zona tiene un costo mensual fijo.",
            savings=0.5,
        )


    @staticmethod
    def private_zone_review_rule(client_id: int):
        return DNSRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('zone_type') == 'Private',
            finding_type="DNS_ZONE_PRIVATE_REVIEW",
            severity="LOW",
            message="Zona DNS privada; confirmar que sigue vinculada a las VNets que la necesitan.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="DNS",
            resource_type="Zone",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:

            existing = AzureFinding.query.filter_by(
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
                    created = AzureFinding.upsert_finding(
                        client_id=client_id,
                        azure_account_id=resource.azure_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        azure_service="DNS",
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

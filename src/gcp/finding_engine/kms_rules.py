from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class KMSRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += KMSRules.global_location_review_rule(client_id)
        total += KMSRules.default_name_review_rule(client_id)
        return total

    @staticmethod
    def global_location_review_rule(client_id: int):
        return KMSRules._evaluate_rule(
            client_id,
            condition=lambda r: r.region == 'global',
            finding_type="KEYRING_GLOBAL_LOCATION_REVIEW",
            severity="LOW",
            message="Key ring en ubicacion global; evaluar si conviene una ubicacion regional por latencia/residencia de datos.",
            savings=0.0,
        )


    @staticmethod
    def default_name_review_rule(client_id: int):
        return KMSRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('name') == 'default',
            finding_type="KEYRING_NAME_DEFAULT",
            severity="LOW",
            message="Key ring con nombre generico 'default'; se recomienda un key ring dedicado por servicio/entorno.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudKMS",
            resource_type="KeyRing",
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
                        gcp_service="CloudKMS",
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

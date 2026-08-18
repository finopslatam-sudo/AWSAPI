from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class FunctionsRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += FunctionsRules.ingress_all_rule(client_id)
        total += FunctionsRules.gen1_review_rule(client_id)
        return total

    @staticmethod
    def ingress_all_rule(client_id: int):
        return FunctionsRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('ingress_settings') == 'ALLOW_ALL',
            finding_type="FUNCTIONS_INGRESS_ALL",
            severity="HIGH",
            message="Cloud Function acepta invocaciones desde cualquier origen (ALLOW_ALL); revisar si deberia restringirse.",
            savings=0.0,
        )


    @staticmethod
    def gen1_review_rule(client_id: int):
        return FunctionsRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('environment') == 'GEN_1',
            finding_type="FUNCTIONS_GEN1_REVIEW",
            severity="LOW",
            message="Cloud Function en 1a generacion; evaluar migrar a 2a generacion (basada en Cloud Run) por mejores limites y precio.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudFunctions",
            resource_type="Function",
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
                        gcp_service="CloudFunctions",
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

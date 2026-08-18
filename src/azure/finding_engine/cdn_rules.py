from src.models.azure_resource_inventory import AzureResourceInventory
from src.models.azure_finding import AzureFinding


class CDNRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += CDNRules.no_endpoints_rule(client_id)
        total += CDNRules.http_allowed_rule(client_id)
        return total

    @staticmethod
    def no_endpoints_rule(client_id: int):
        return CDNRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("endpoint_count", 0) == 0,
            finding_type="CDN_PROFILE_NO_ENDPOINTS",
            severity="MEDIUM",
            message="Perfil de CDN sin ningún endpoint configurado; sigue facturando su tier base sin distribuir contenido.",
            savings=10.0,
        )

    @staticmethod
    def http_allowed_rule(client_id: int):
        return CDNRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get("any_http_allowed") is True,
            finding_type="CDN_HTTP_ALLOWED",
            severity="MEDIUM",
            message="Al menos un endpoint del perfil de CDN permite tráfico HTTP sin cifrar; restringir a HTTPS únicamente.",
            savings=0.0,
        )

    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AzureResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CDN",
            resource_type="Profile",
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
                        azure_service="CDN",
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

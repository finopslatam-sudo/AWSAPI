from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class RedisRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += RedisRules.basic_tier_review_rule(client_id)
        total += RedisRules.no_auth_network_rule(client_id)
        return total

    @staticmethod
    def basic_tier_review_rule(client_id: int):
        return RedisRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('tier') == 'BASIC',
            finding_type="REDIS_BASIC_TIER_REVIEW",
            severity="MEDIUM",
            message="Instancia Memorystore en tier Basic (sin alta disponibilidad/failover); evaluar si el caso de uso requiere tier Standard.",
            savings=0.0,
        )


    @staticmethod
    def no_auth_network_rule(client_id: int):
        return RedisRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('authorized_network') is None,
            finding_type="REDIS_NO_AUTH_NETWORK",
            severity="LOW",
            message="Instancia Memorystore sin red autorizada explicita configurada.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="Memorystore",
            resource_type="RedisInstance",
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
                        gcp_service="Memorystore",
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

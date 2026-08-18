from src.models.gcp_resource_inventory import GCPResourceInventory
from src.models.gcp_finding import GCPFinding


class LoggingRules:

    @staticmethod
    def run_all(client_id: int):
        total = 0
        total += LoggingRules.unlimited_retention_rule(client_id)
        total += LoggingRules.not_locked_rule(client_id)
        return total

    @staticmethod
    def unlimited_retention_rule(client_id: int):
        return LoggingRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('retention_days', 0) > 90,
            finding_type="LOGGING_RETENTION_HIGH",
            severity="LOW",
            message="Log bucket con retencion mayor a 90 dias; revisar si es necesario o si conviene exportar a Cloud Storage y reducir la retencion.",
            savings=0.0,
        )


    @staticmethod
    def not_locked_rule(client_id: int):
        return LoggingRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata or {}).get('locked') is not True,
            finding_type="LOGGING_BUCKET_NOT_LOCKED",
            severity="LOW",
            message="Log bucket sin 'lock' de retencion; cualquiera con permisos puede reducir la retencion configurada.",
            savings=0.0,
        )


    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = GCPResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudLogging",
            resource_type="LogBucket",
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
                        gcp_service="CloudLogging",
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

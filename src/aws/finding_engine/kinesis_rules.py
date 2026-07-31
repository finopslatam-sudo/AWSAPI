from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class KinesisRules:

    @staticmethod
    def run_all(client_id: int):
        return KinesisRules.extended_retention_rule(client_id)

    # =====================================================
    # RETENCIÓN EXTENDIDA (> 24H, TIENE COSTO ADICIONAL)
    # =====================================================
    @staticmethod
    def extended_retention_rule(client_id: int):

        finding_type = "KINESIS_EXTENDED_RETENTION"
        severity = "MEDIUM"
        message = "Stream de Kinesis con retención extendida (> 24 horas); este período adicional tiene costo por shard-hora. Revisar si es necesario para el caso de uso."
        savings = 0

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="Kinesis",
            resource_type="Stream",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:
            metadata = resource.resource_metadata or {}
            has_extended_retention = (metadata.get("retention_period_hours") or 0) > 24

            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=resource.resource_id,
                finding_type=finding_type
            ).first()

            if has_extended_retention:
                if existing:
                    existing.resolved = False
                    existing.message = message
                    existing.severity = severity
                else:
                    created = AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=resource.aws_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        aws_service="Kinesis",
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

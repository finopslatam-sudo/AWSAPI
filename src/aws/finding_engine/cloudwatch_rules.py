from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding
from src.models.database import db
from datetime import datetime


class CloudWatchRules:

    @staticmethod
    def run_all(client_id: int):

        total = 0
        total += CloudWatchRules.unlimited_retention_rule(client_id)
        total += CloudWatchRules.high_retention_rule(client_id)

        return total

    # =====================================================
    # UNLIMITED RETENTION
    # =====================================================
    @staticmethod
    def unlimited_retention_rule(client_id: int):

        return CloudWatchRules._evaluate_rule(
            client_id,
            condition=lambda r: r.resource_metadata.get("retention_in_days") is None,
            finding_type="CLOUDWATCH_NO_RETENTION",
            severity="HIGH",
            message="Log group has unlimited retention.",
            savings=5
        )

    # =====================================================
    # HIGH RETENTION
    # =====================================================
    @staticmethod
    def high_retention_rule(client_id: int):

        return CloudWatchRules._evaluate_rule(
            client_id,
            condition=lambda r: (r.resource_metadata.get("retention_in_days") or 0) > 90,
            finding_type="CLOUDWATCH_HIGH_RETENTION",
            severity="MEDIUM",
            message="Log retention is higher than 90 days.",
            savings=3
        )

    # =====================================================
    # CORE ENGINE
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="CloudWatch",
            resource_type="LogGroup",
            is_active=True
        ).all()

        findings_created = 0

        for resource in resources:

            if condition(resource):

                exists = AWSFinding.query.filter_by(
                    client_id=client_id,
                    resource_id=resource.resource_id,
                    finding_type=finding_type,
                    resolved=False
                ).first()

                if not exists:
                    finding = AWSFinding(
                        client_id=client_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        finding_type=finding_type,
                        severity=severity,
                        message=message,
                        estimated_monthly_savings=savings,
                        resolved=False,
                        detected_at=datetime.utcnow(),
                        created_at=datetime.utcnow()
                    )

                    db.session.add(finding)
                    findings_created += 1

        return findings_created
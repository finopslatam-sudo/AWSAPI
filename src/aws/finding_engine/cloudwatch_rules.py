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
    # CORE ENGINE (IDEMPOTENT)
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

            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=resource.resource_id,
                finding_type=finding_type
            ).first()

            if condition(resource):

                if existing:
                    existing.resolved = False
                    existing.detected_at = datetime.utcnow()
                    existing.message = message
                    existing.severity = severity
                    existing.estimated_monthly_savings = savings
                else:
                    finding = AWSFinding(
                        client_id=client_id,
                        aws_account_id=resource.aws_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        aws_service="CloudWatch",
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

            else:
                if existing and not existing.resolved:
                    existing.resolved = True
                    existing.resolved_at = datetime.utcnow()

        return findings_created
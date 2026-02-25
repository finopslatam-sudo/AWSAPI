from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding
from src.models.database import db
from datetime import datetime


class LambdaRules:

    @staticmethod
    def run_all(client_id: int):

        total = 0
        total += LambdaRules.memory_overprovision_rule(client_id)
        total += LambdaRules.deprecated_runtime_rule(client_id)

        return total

    # =====================================================
    # MEMORY OVERPROVISION
    # =====================================================
    @staticmethod
    def memory_overprovision_rule(client_id: int):

        return LambdaRules._evaluate_rule(
            client_id,
            condition=lambda r: r.resource_metadata.get("memory_size", 0) > 1024,
            finding_type="LAMBDA_HIGH_MEMORY",
            severity="MEDIUM",
            message="Lambda memory allocation is high (>1024MB). Consider rightsizing.",
            savings=5
        )

    # =====================================================
    # DEPRECATED RUNTIME
    # =====================================================
    @staticmethod
    def deprecated_runtime_rule(client_id: int):

        deprecated = ["python3.7", "nodejs12.x"]

        return LambdaRules._evaluate_rule(
            client_id,
            condition=lambda r: r.resource_metadata.get("runtime") in deprecated,
            finding_type="LAMBDA_DEPRECATED_RUNTIME",
            severity="HIGH",
            message="Lambda runtime is deprecated.",
            savings=0
        )

    # =====================================================
    # CORE ENGINE
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="Lambda",
            resource_type="Function",
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
                        aws_account_id=resource.aws_account_id,
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
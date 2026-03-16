from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class LambdaRules:

    @staticmethod
    def run_all(client_id: int):

        total = 0
        total += LambdaRules.memory_overprovision_rule(client_id)
        total += LambdaRules.deprecated_runtime_rule(client_id)

        return total

    @staticmethod
    def memory_overprovision_rule(client_id: int):

        return LambdaRules._evaluate_rule(
            client_id,
            condition=lambda r: r.resource_metadata.get("memory_size", 0) > 1024,
            finding_type="LAMBDA_HIGH_MEMORY",
            severity="MEDIUM",
            message="Lambda memory allocation is high (>1024MB). Consider rightsizing.",
            savings=0
        )

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

            existing = AWSFinding.query.filter_by(
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
                    created = AWSFinding.upsert_finding(
                        client_id=client_id,
                        aws_account_id=resource.aws_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        aws_service="Lambda",
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

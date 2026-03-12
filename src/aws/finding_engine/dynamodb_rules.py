from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding
from src.models.database import db
from datetime import datetime


class DynamoDBRules:

    @staticmethod
    def run_all(client_id: int):

        total = 0
        total += DynamoDBRules.provisioned_mode_rule(client_id)
        total += DynamoDBRules.empty_table_rule(client_id)

        return total

    # =====================================================
    # PROVISIONED MODE
    # =====================================================
    @staticmethod
    def provisioned_mode_rule(client_id: int):

        return DynamoDBRules._evaluate_rule(
            client_id,
            condition=lambda r: r.resource_metadata.get("billing_mode") == "PROVISIONED",
            finding_type="DYNAMODB_PROVISIONED_MODE",
            severity="MEDIUM",
            message="DynamoDB table is using provisioned mode. Consider On-Demand.",
            savings=8
        )

    # =====================================================
    # EMPTY TABLE
    # =====================================================
    @staticmethod
    def empty_table_rule(client_id: int):

        return DynamoDBRules._evaluate_rule(
            client_id,
            condition=lambda r: r.resource_metadata.get("item_count", 0) == 0,
            finding_type="DYNAMODB_EMPTY_TABLE",
            severity="LOW",
            message="DynamoDB table has zero items.",
            savings=2
        )

    # =====================================================
    # CORE ENGINE
    # =====================================================
    @staticmethod
    def _evaluate_rule(client_id, condition, finding_type, severity, message, savings):

        resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="DynamoDB",
            resource_type="Table",
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
                    existing.estimated_monthly_savings = savings
                else:
                    finding = AWSFinding(
                        client_id=client_id,
                        aws_account_id=resource.aws_account_id,
                        resource_id=resource.resource_id,
                        resource_type=resource.resource_type,
                        region=resource.region,
                        aws_service="DynamoDB",
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
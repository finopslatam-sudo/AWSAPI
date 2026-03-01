from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class SavingsPlanRules:

    @staticmethod
    def review_active_plans_rule(client_id):

        plans = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="SavingsPlans",
            is_active=True
        ).all()

        findings_created = 0

        for plan in plans:

            existing = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_id=plan.resource_id,
                finding_type="SP_REVIEW"
            ).first()

            if existing:
                existing.resolved = False
            else:
                created = AWSFinding.upsert_finding(
                    client_id=client_id,
                    aws_account_id=plan.aws_account_id,
                    resource_id=plan.resource_id,
                    resource_type="SavingsPlan",
                    aws_service=plan.service_name,
                    finding_type="SP_REVIEW",
                    severity="MEDIUM",
                    message="Savings Plan active — verify utilization coverage",
                    estimated_monthly_savings=None
                )
                if created:
                    findings_created += 1

        return findings_created
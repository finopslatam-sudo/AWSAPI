from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding
from src.models.database import db
from datetime import datetime


class SavingsPlanRules:

    @staticmethod
    def review_active_plans_rule(client_id):

        count = 0

        plans = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            service_name="SavingsPlans",
            is_active=True
        ).all()

        for plan in plans:

            finding = AWSFinding(
                client_id=client_id,
                aws_account_id=plan.aws_account_id,
                resource_id=plan.resource_id,
                resource_type="SavingsPlan",
                finding_type="SP_REVIEW",
                severity="MEDIUM",
                message="Savings Plan active — verify utilization coverage",
                estimated_monthly_savings=None,
                resolved=False,
                detected_at=datetime.utcnow(),
                created_at=datetime.utcnow()
            )

            db.session.add(finding)
            count += 1

        return count
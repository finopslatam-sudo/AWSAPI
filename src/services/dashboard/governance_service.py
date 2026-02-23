from sqlalchemy import func
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db


class GovernanceService:

    # =====================================================
    # GOVERNANCE SCORE
    # =====================================================
    @staticmethod
    def get_governance_score(client_id: int):

        total_resources = db.session.query(
            AWSResourceInventory.id
        ).filter_by(
            client_id=client_id,
            is_active=True
        ).count()

        if total_resources == 0:
            return {
                "total_resources": 0,
                "non_compliant_resources": 0,
                "compliant_resources": 0,
                "compliance_percentage": 100.0
            }

        non_compliant_resources = db.session.query(
            func.count(func.distinct(AWSFinding.resource_id))
        ).filter(
            AWSFinding.client_id == client_id,
            AWSFinding.resolved == False,
            AWSFinding.finding_type.like("MISSING_TAG%")
        ).scalar() or 0

        compliant_resources = total_resources - non_compliant_resources

        compliance_percentage = round(
            (compliant_resources / total_resources) * 100,
            2
        )

        return {
            "total_resources": total_resources,
            "non_compliant_resources": non_compliant_resources,
            "compliant_resources": compliant_resources,
            "compliance_percentage": compliance_percentage
        }

 
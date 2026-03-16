from sqlalchemy import func, and_
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db


class GovernanceService:

    # =====================================================
    # GOVERNANCE SCORE (ENTERPRISE READY)
    # =====================================================
    @staticmethod
    def get_governance_score(
        client_id: int,
        aws_account_id: int | None = None
    ):

        # -----------------------------------------------------
        # TOTAL ACTIVE RESOURCES
        # -----------------------------------------------------
        total_resources_query = db.session.query(
            func.count(AWSResourceInventory.id)
        ).filter(
            AWSResourceInventory.client_id == client_id,
            AWSResourceInventory.is_active.is_(True)
        )

        if aws_account_id is not None:
            total_resources_query = total_resources_query.filter(
                AWSResourceInventory.aws_account_id == aws_account_id
            )

        total_resources = total_resources_query.scalar() or 0

        if total_resources == 0:
            return {
                "total_resources": 0,
                "non_compliant_resources": 0,
                "compliant_resources": 0,
                "compliance_percentage": 100.0
            }

        # -----------------------------------------------------
        # NON-COMPLIANT RESOURCES
        # (Governance-related unresolved findings)
        # -----------------------------------------------------
        non_compliant_resources_query = (
            db.session.query(
                func.count(func.distinct(AWSResourceInventory.id))
            )
            .join(
                AWSFinding,
                and_(
                    AWSFinding.resource_id == AWSResourceInventory.resource_id,
                    AWSFinding.client_id == AWSResourceInventory.client_id,
                    AWSFinding.resolved.is_(False),
                    AWSFinding.finding_type.like("MISSING_%")
                )
            )
            .filter(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.is_active.is_(True)
            )
        )

        if aws_account_id is not None:
            non_compliant_resources_query = non_compliant_resources_query.filter(
                AWSResourceInventory.aws_account_id == aws_account_id,
                AWSFinding.aws_account_id == aws_account_id
            )

        non_compliant_resources = (
            non_compliant_resources_query.scalar() or 0
        )

        compliant_resources = max(
            total_resources - non_compliant_resources,
            0
        )

        compliance_percentage = round(
            (compliant_resources / total_resources) * 100,
            2
        )

        # -----------------------------------------------------
        # Governance Maturity Level
        # -----------------------------------------------------
        if compliance_percentage >= 95:
            maturity_level = "EXCELLENT"
        elif compliance_percentage >= 85:
            maturity_level = "GOOD"
        elif compliance_percentage >= 70:
            maturity_level = "FAIR"
        else:
            maturity_level = "POOR"

        return {
            "total_resources": total_resources,
            "non_compliant_resources": non_compliant_resources,
            "compliant_resources": compliant_resources,
            "compliance_percentage": compliance_percentage,
            "maturity_level": maturity_level
        }

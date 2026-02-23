from sqlalchemy import func
from src.models.aws_finding import AWSFinding
from src.models.database import db
from src.services.dashboard.risk_service import RiskService
from src.services.dashboard.governance_service import GovernanceService


class ExecutiveService:

    # =====================================================
    # EXECUTIVE SUMMARY ENGINE
    # =====================================================
    @staticmethod
    def get_executive_summary(client_id: int):

        risk = RiskService.get_risk_score(client_id)
        governance = GovernanceService.get_governance_score(client_id)
        priority = RiskService.get_priority_services(client_id)

        # ---------------- PRIMARY RISK DRIVER ----------------
        primary_service = priority[0]["service"] if priority else None

        # ---------------- OVERALL POSTURE ----------------
        overall_posture = risk["risk_level"]

        # ---------------- GOVERNANCE STATUS ----------------
        compliance = governance["compliance_percentage"]

        if compliance >= 80:
            governance_status = "HEALTHY"
        elif compliance >= 60:
            governance_status = "MODERATE"
        elif compliance >= 40:
            governance_status = "HIGH_RISK"
        else:
            governance_status = "CRITICAL"

        # ---------------- FINANCIAL IMPACT ----------------
        savings = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        savings = float(savings)

        # ---------------- NARRATIVE GENERATION ----------------
        message = (
            f"Your cloud environment currently has a {overall_posture} risk posture "
            f"with {governance_status} governance compliance. "
        )

        if primary_service:
            message += f"{primary_service} is the primary risk driver. "

        if savings > 0:
            message += (
                f"Identified potential monthly savings of ${round(savings, 2)} "
                f"through remediation of active findings."
            )
        else:
            message += "No immediate financial savings opportunities were detected."

        return {
            "overall_posture": overall_posture,
            "primary_risk_driver": primary_service,
            "governance_status": governance_status,
            "financial_exposure": round(savings, 2),
            "message": message
        }
    
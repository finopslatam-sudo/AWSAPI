from sqlalchemy import func, and_
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_account import AWSAccount
from src.models.database import db
from src.services.dashboard.risk_service import RiskService
from src.services.dashboard.governance_service import GovernanceService
from src.services.dashboard.roi_service import ROIService


class ExecutiveService:

    # =====================================================
    # EXECUTIVE SUMMARY ENGINE (ENTERPRISE READY)
    # =====================================================
    @staticmethod
    def get_executive_summary(client_id: int):

        # -----------------------------------------------------
        # CORE METRICS
        # -----------------------------------------------------
        risk = RiskService.get_risk_score(client_id)
        governance = GovernanceService.get_governance_score(client_id)
        roi = ROIService.get_roi_projection(client_id)
        priority = RiskService.get_priority_services(client_id)

        # -----------------------------------------------------
        # PRIMARY RISK DRIVER
        # -----------------------------------------------------
        primary_service = priority[0]["service"] if priority else None

        # -----------------------------------------------------
        # FINANCIAL EXPOSURE (ACTIVE FINDINGS ONLY + INVENTORY ACTIVE)
        # -----------------------------------------------------
        monthly_exposure = (
            db.session.query(
                func.sum(AWSFinding.estimated_monthly_savings)
            )
            .join(
                AWSResourceInventory,
                and_(
                    AWSFinding.resource_id == AWSResourceInventory.resource_id,
                    AWSFinding.client_id == AWSResourceInventory.client_id
                )
            )
            .filter(
                AWSFinding.client_id == client_id,
                AWSFinding.resolved.is_(False),
                AWSResourceInventory.is_active.is_(True)
            )
            .scalar() or 0
        )

        monthly_exposure = float(monthly_exposure)
        annual_exposure = round(monthly_exposure * 12, 2)

        # -----------------------------------------------------
        # GOVERNANCE STATUS CLASSIFICATION
        # -----------------------------------------------------
        compliance = governance["compliance_percentage"]

        if compliance >= 95:
            governance_status = "EXCELLENT"
        elif compliance >= 85:
            governance_status = "GOOD"
        elif compliance >= 70:
            governance_status = "FAIR"
        else:
            governance_status = "POOR"

        # -----------------------------------------------------
        # URGENCY LEVEL (BASED ON RISK)
        # -----------------------------------------------------
        urgency_level = ExecutiveService._calculate_urgency(
            risk["risk_level"]
        )

        # -----------------------------------------------------
        # ACCOUNT FOOTPRINT
        # -----------------------------------------------------
        accounts_count = (
            AWSAccount.query.filter_by(
                client_id=client_id,
                is_active=True
            ).count()
        )

        # -----------------------------------------------------
        # NARRATIVE GENERATION
        # -----------------------------------------------------
        narrative = ExecutiveService._build_narrative(
            risk_level=risk["risk_level"],
            risk_score=risk["risk_score"],
            governance_status=governance_status,
            primary_service=primary_service,
            monthly_exposure=monthly_exposure,
            annual_exposure=annual_exposure,
            accounts_count=accounts_count,
            projected_risk_score=roi["projected_risk_score"]
        )

        return {
            "overall_posture": risk["risk_level"],
            "risk_score": risk["risk_score"],
            "urgency_level": urgency_level,
            "primary_risk_driver": primary_service,
            "governance_status": governance_status,
            "governance_score": compliance,
            "monthly_financial_exposure": round(monthly_exposure, 2),
            "annual_financial_exposure": annual_exposure,
            "projected_risk_score_after_high_remediation": roi["projected_risk_score"],
            "accounts_covered": accounts_count,
            "message": narrative
        }

    # =====================================================
    # INTERNAL: URGENCY CALCULATOR
    # =====================================================
    @staticmethod
    def _calculate_urgency(risk_level: str):

        mapping = {
            "LOW": "MONITOR",
            "MODERATE": "ATTENTION_REQUIRED",
            "HIGH": "PRIORITY_ACTION",
            "CRITICAL": "IMMEDIATE_ACTION"
        }

        return mapping.get(risk_level, "MONITOR")

    # =====================================================
    # INTERNAL: EXECUTIVE NARRATIVE BUILDER
    # =====================================================
    @staticmethod
    def _build_narrative(
        risk_level,
        risk_score,
        governance_status,
        primary_service,
        monthly_exposure,
        annual_exposure,
        accounts_count,
        projected_risk_score
    ):

        message = (
            f"The organization currently operates with a {risk_level} risk posture "
            f"(score: {risk_score}) across {accounts_count} connected account(s). "
        )

        message += (
            f"Governance maturity is classified as {governance_status}. "
        )

        if primary_service:
            message += (
                f"The primary risk driver is {primary_service}, "
                f"which should be prioritized for remediation. "
            )

        if monthly_exposure > 0:
            message += (
                f"Current financial exposure is estimated at "
                f"${round(monthly_exposure, 2)} per month "
                f"(${annual_exposure} annually). "
            )

            message += (
                f"Remediation of high-severity findings alone "
                f"would improve the risk score to approximately "
                f"{projected_risk_score}. "
            )
        else:
            message += (
                "No significant immediate financial exposure has been identified. "
            )

        return message.strip()
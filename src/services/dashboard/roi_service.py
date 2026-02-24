from sqlalchemy import func, case, and_
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db


class ROIService:

    # =====================================================
    # ROI PROJECTION ENGINE (ENTERPRISE READY)
    # =====================================================
    @staticmethod
    def get_roi_projection(client_id: int):

        # -----------------------------------------------------
        # TOTAL ACTIVE RESOURCES
        # -----------------------------------------------------
        total_resources = (
            db.session.query(func.count(AWSResourceInventory.id))
            .filter(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.is_active.is_(True)
            )
            .scalar() or 0
        )

        if total_resources == 0:
            return {
                "projected_risk_score": 100.0,
                "projected_risk_level": "LOW",
                "projected_governance": 100.0,
                "high_savings_opportunity_monthly": 0.0,
                "high_savings_opportunity_annual": 0.0
            }

        # -----------------------------------------------------
        # AGGREGATED ACTIVE FINDINGS (JOIN INVENTORY ACTIVO)
        # -----------------------------------------------------
        results = (
            db.session.query(
                func.sum(case((AWSFinding.severity == "HIGH", 1), else_=0)).label("high"),
                func.sum(case((AWSFinding.severity == "MEDIUM", 1), else_=0)).label("medium"),
                func.sum(case((AWSFinding.severity == "LOW", 1), else_=0)).label("low"),
                func.sum(
                    case(
                        (AWSFinding.severity == "HIGH",
                         AWSFinding.estimated_monthly_savings),
                        else_=0
                    )
                ).label("high_savings")
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
            .first()
        )

        high = results.high or 0
        medium = results.medium or 0
        low = results.low or 0
        high_savings = float(results.high_savings or 0)

        # -----------------------------------------------------
        # SIMULACIÓN: HIGH RESUELTOS
        # -----------------------------------------------------
        simulated_high = 0
        simulated_medium = medium
        simulated_low = low

        risk_points = (simulated_high * 5) + (simulated_medium * 3) + (simulated_low * 1)
        max_risk = total_resources * 5

        projected_risk_score = 100 - ((risk_points / max_risk) * 100)
        projected_risk_score = round(projected_risk_score, 2)

        projected_risk_level = ROIService._calculate_risk_level(projected_risk_score)

        # -----------------------------------------------------
        # GOVERNANCE PROJECTION
        # Simulamos remediación HIGH governance findings
        # -----------------------------------------------------
        non_compliant_resources = (
            db.session.query(
                func.count(func.distinct(AWSResourceInventory.id))
            )
            .join(
                AWSFinding,
                and_(
                    AWSFinding.resource_id == AWSResourceInventory.resource_id,
                    AWSFinding.client_id == AWSResourceInventory.client_id,
                    AWSFinding.resolved.is_(False),
                    AWSFinding.finding_type.like("MISSING_%"),
                    AWSFinding.severity != "HIGH"
                )
            )
            .filter(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.is_active.is_(True)
            )
            .scalar() or 0
        )

        compliant_resources = max(
            total_resources - non_compliant_resources,
            0
        )

        projected_governance = round(
            (compliant_resources / total_resources) * 100,
            2
        )

        # -----------------------------------------------------
        # FINANCIAL IMPACT
        # -----------------------------------------------------
        monthly_savings = round(high_savings, 2)
        annual_savings = round(high_savings * 12, 2)

        return {
            "projected_risk_score": projected_risk_score,
            "projected_risk_level": projected_risk_level,
            "projected_governance": projected_governance,
            "high_savings_opportunity_monthly": monthly_savings,
            "high_savings_opportunity_annual": annual_savings
        }

    # =====================================================
    # INTERNAL RISK LEVEL CALCULATOR
    # =====================================================
    @staticmethod
    def _calculate_risk_level(score: float):

        if score >= 80:
            return "LOW"
        elif score >= 60:
            return "MODERATE"
        elif score >= 40:
            return "HIGH"
        else:
            return "CRITICAL"
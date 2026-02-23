from sqlalchemy import func
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db


class ROIService:

    # =====================================================
    # ROI PROJECTION ENGINE
    # =====================================================
    @staticmethod
    def get_roi_projection(client_id: int):

        # ---------------- CURRENT STATE ----------------
        total_resources = db.session.query(
            AWSResourceInventory.id
        ).filter_by(
            client_id=client_id,
            is_active=True
        ).count()

        if total_resources == 0:
            return {
                "projected_risk_score": 100.0,
                "projected_risk_level": "LOW",
                "projected_governance": 100.0,
                "high_savings_opportunity": 0.0
            }

        # ---------------- ACTIVE FINDINGS ----------------
        high_findings = AWSFinding.query.filter_by(
            client_id=client_id,
            severity="HIGH",
            resolved=False
        ).all()

        medium = AWSFinding.query.filter_by(
            client_id=client_id,
            severity="MEDIUM",
            resolved=False
        ).count()

        low = AWSFinding.query.filter_by(
            client_id=client_id,
            severity="LOW",
            resolved=False
        ).count()

        # ---------------- SIMULATION ----------------
        # Simulamos HIGH = 0 (remediados)
        simulated_high = 0

        risk_points = (simulated_high * 5) + (medium * 3) + (low * 1)
        max_risk = total_resources * 5

        projected_risk_score = 100 - ((risk_points / max_risk) * 100) if max_risk else 100
        projected_risk_score = round(projected_risk_score, 2)

        # ---------------- RISK LEVEL ----------------
        if projected_risk_score >= 80:
            projected_risk_level = "LOW"
        elif projected_risk_score >= 60:
            projected_risk_level = "MODERATE"
        elif projected_risk_score >= 40:
            projected_risk_level = "HIGH"
        else:
            projected_risk_level = "CRITICAL"

        # ---------------- GOVERNANCE PROJECTION ----------------
        non_compliant_resources = db.session.query(
            func.count(func.distinct(AWSFinding.resource_id))
        ).filter(
            AWSFinding.client_id == client_id,
            AWSFinding.resolved == False,
            AWSFinding.finding_type.like("MISSING_TAG%"),
            AWSFinding.severity != "HIGH"
        ).scalar() or 0

        compliant_resources = total_resources - non_compliant_resources

        projected_governance = round(
            (compliant_resources / total_resources) * 100,
            2
        )

        # ---------------- HIGH SAVINGS ----------------
        high_savings = sum(
            float(f.estimated_monthly_savings or 0)
            for f in high_findings
        )

        return {
            "projected_risk_score": projected_risk_score,
            "projected_risk_level": projected_risk_level,
            "projected_governance": projected_governance,
            "high_savings_opportunity": round(high_savings, 2)
        }
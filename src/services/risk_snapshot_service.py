from datetime import datetime
from src.models.risk_snapshot import RiskSnapshot
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db
from src.services.dashboard.risk_service import RiskService
from src.services.dashboard.governance_service import GovernanceService
from sqlalchemy import func


class RiskSnapshotService:

    @staticmethod
    def create_snapshot(client_id: int):

        # ===============================
        # RISK
        # ===============================
        risk_data = RiskService.get_risk_score(client_id)

        # ===============================
        # GOVERNANCE
        # ===============================
        governance_data = GovernanceService.get_governance_score(client_id)

        # ===============================
        # FINANCIAL EXPOSURE
        # ===============================
        financial_exposure = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        # ===============================
        # TOTAL FINDINGS
        # ===============================
        total_findings = AWSFinding.query.filter_by(
            client_id=client_id,
            resolved=False
        ).count()

        snapshot = RiskSnapshot(
            client_id=client_id,
            risk_score=risk_data["risk_score"],
            risk_level=risk_data["risk_level"],
            governance_percentage=governance_data["compliance_percentage"],
            financial_exposure=float(financial_exposure),
            total_findings=total_findings,
            created_at=datetime.utcnow()
        )

        db.session.add(snapshot)
        db.session.commit()

        return snapshot
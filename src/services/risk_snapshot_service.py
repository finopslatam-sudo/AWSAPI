from src.models.risk_snapshot import RiskSnapshot
from src.models.database import db
from src.services.client_dashboard_service import ClientDashboardService

class RiskSnapshotService:

    @staticmethod
    def create_snapshot(client_id: int):

        summary = ClientDashboardService.get_summary(client_id)

        risk = summary["risk"]
        governance = summary["governance"]
        findings = summary["findings"]

        snapshot = RiskSnapshot(
            client_id=client_id,
            risk_score=risk["risk_score"],
            risk_level=risk["risk_level"],
            governance_percentage=governance["compliance_percentage"],
            total_resources=governance["total_resources"],
            total_findings=findings["active"],
            financial_exposure=findings["estimated_monthly_savings"]
        )

        db.session.add(snapshot)
        db.session.commit()

        return snapshot
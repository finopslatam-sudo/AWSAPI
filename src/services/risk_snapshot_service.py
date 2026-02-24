from datetime import datetime
from sqlalchemy import func
from src.models.risk_snapshot import RiskSnapshot
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db
from src.services.dashboard.risk_service import RiskService
from src.services.dashboard.governance_service import GovernanceService


class RiskSnapshotService:

    @staticmethod
    def create_snapshot(client_id: int):

        today = datetime.utcnow().date()

        # ===============================
        # CALCULAR MÉTRICAS
        # ===============================
        risk_data = RiskService.get_risk_score(client_id)
        governance_data = GovernanceService.get_governance_score(client_id)

        total_resources = AWSResourceInventory.query.filter_by(
            client_id=client_id,
            is_active=True
        ).count()

        total_findings = AWSFinding.query.filter_by(
            client_id=client_id,
            resolved=False
        ).count()

        financial_exposure = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        # ===============================
        # BUSCAR SNAPSHOT DEL DÍA
        # ===============================
        existing_snapshot = (
            RiskSnapshot.query
            .filter(
                RiskSnapshot.client_id == client_id,
                func.date(RiskSnapshot.created_at) == today
            )
            .first()
        )

        if existing_snapshot:
            # UPDATE
            existing_snapshot.risk_score = risk_data["risk_score"]
            existing_snapshot.risk_level = risk_data["risk_level"]
            existing_snapshot.governance_percentage = governance_data["compliance_percentage"]
            existing_snapshot.total_resources = total_resources
            existing_snapshot.total_findings = total_findings
            existing_snapshot.financial_exposure = float(financial_exposure)

            db.session.commit()
            return existing_snapshot

        # ===============================
        # CREAR NUEVO SNAPSHOT
        # ===============================
        snapshot = RiskSnapshot(
            client_id=client_id,
            risk_score=risk_data["risk_score"],
            risk_level=risk_data["risk_level"],
            governance_percentage=governance_data["compliance_percentage"],
            total_resources=total_resources,
            total_findings=total_findings,
            financial_exposure=float(financial_exposure),
            created_at=datetime.utcnow()
        )

        db.session.add(snapshot)
        db.session.commit()

        return snapshot
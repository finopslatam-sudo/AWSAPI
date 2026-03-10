from datetime import datetime
from sqlalchemy import func

from src.models.risk_snapshot import RiskSnapshot
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db

from src.services.dashboard.governance_service import GovernanceService
from src.services.inventory.inventory_service import InventoryService


class RiskSnapshotService:

    @staticmethod
    def create_snapshot(client_id: int):

        today = datetime.utcnow().date()

        # =====================================================
        # 1️⃣ GLOBAL HEALTH (Inventory Engine)
        # =====================================================
        health_data = InventoryService.get_global_health_score(client_id)

        # =====================================================
        # 2️⃣ GOVERNANCE
        # =====================================================
        governance_data = GovernanceService.get_governance_score(client_id)

        # =====================================================
        # 3️⃣ FINANCIAL EXPOSURE
        # =====================================================
        financial_exposure = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        # =====================================================
        # 4️⃣ BUSCAR SNAPSHOT DEL DÍA
        # =====================================================
        existing_snapshot = (
            RiskSnapshot.query
            .filter(
                RiskSnapshot.client_id == client_id,
                func.date(RiskSnapshot.created_at) == today
            )
            .first()
        )

        # =====================================================
        # 5️⃣ UPDATE SNAPSHOT EXISTENTE
        # =====================================================
        if existing_snapshot:

            existing_snapshot.health_score = health_data["health_score"]
            existing_snapshot.risk_level = health_data["risk_level"]

            existing_snapshot.total_resources = health_data["total_resources"]
            existing_snapshot.total_findings = health_data["total_findings"]

            existing_snapshot.high_count = health_data["high"]
            existing_snapshot.medium_count = health_data["medium"]
            existing_snapshot.low_count = health_data["low"]

            existing_snapshot.governance_percentage = governance_data["compliance_percentage"]
            existing_snapshot.financial_exposure = float(financial_exposure)
            existing_snapshot.created_at = datetime.utcnow()

            db.session.commit()
            return existing_snapshot

        # =====================================================
        # 6️⃣ CREAR NUEVO SNAPSHOT
        # =====================================================
        snapshot = RiskSnapshot(
            client_id=client_id,

            health_score=health_data["health_score"],
            risk_level=health_data["risk_level"],

            total_resources=health_data["total_resources"],
            total_findings=health_data["total_findings"],

            high_count=health_data["high"],
            medium_count=health_data["medium"],
            low_count=health_data["low"],

            governance_percentage=governance_data["compliance_percentage"],
            financial_exposure=float(financial_exposure),

            created_at=datetime.utcnow()
        )

        db.session.add(snapshot)
        db.session.commit()

        return snapshot
    
    # =====================================================
    # GET LAST SCAN
    # =====================================================
    @staticmethod
    def get_last_scan(client_id: int):

        last_snapshot = (
            RiskSnapshot.query
            .filter(RiskSnapshot.client_id == client_id)
            .order_by(RiskSnapshot.created_at.desc())
            .first()
        )

        if not last_snapshot:
            return None

        return last_snapshot.created_at
from sqlalchemy import func, and_
from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db

from src.services.dashboard.risk_service import RiskService
from src.services.dashboard.governance_service import GovernanceService
from src.services.dashboard.executive_service import ExecutiveService
from src.services.dashboard.roi_service import ROIService
from src.services.dashboard.trend_service import TrendService
from src.services.dashboard.remediation_service import RemediationService
from src.services.client_findings_service import ClientFindingsService


class ClientDashboardFacade:

    @staticmethod
    def get_summary(client_id: int):

        # =====================================================
        # FINDINGS STATS (Delegado al servicio optimizado)
        # =====================================================
        findings_stats = ClientFindingsService.get_stats(client_id)

        # =====================================================
        # ACCOUNTS SUMMARY
        # =====================================================
        accounts_data = (
            db.session.query(
                func.count(AWSAccount.id).label("accounts_count"),
                func.max(AWSAccount.last_sync).label("last_sync")
            )
            .filter(
                AWSAccount.client_id == client_id,
                AWSAccount.is_active.is_(True)
            )
            .first()
        )

        # =====================================================
        # RESOURCES AFFECTED (solo inventory activo)
        # =====================================================
        resources_affected = (
            db.session.query(
                func.count(func.distinct(AWSFinding.resource_id))
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

        # =====================================================
        # DELEGATED SERVICES
        # =====================================================
        governance = GovernanceService.get_governance_score(client_id)
        risk = RiskService.get_risk_score(client_id)
        risk_by_service = RiskService.get_risk_breakdown_by_service(client_id)
        priority_services = RiskService.get_priority_services(client_id)
        executive_summary = ExecutiveService.get_executive_summary(client_id)
        roi_projection = ROIService.get_roi_projection(client_id)
        trend = TrendService.get_risk_trend(client_id, 30)
        remediation = RemediationService.get_remediation_metrics(client_id, 30)

        return {
            "findings": findings_stats,
            "accounts": accounts_data.accounts_count or 0,
            "last_sync": accounts_data.last_sync.isoformat() if accounts_data.last_sync else None,
            "resources_affected": resources_affected,
            "governance": governance,
            "risk": risk,
            "risk_by_service": risk_by_service,
            "priority_services": priority_services,
            "executive_summary": executive_summary,
            "roi_projection": roi_projection,
            "trend": trend,
            "remediation": remediation,
        }
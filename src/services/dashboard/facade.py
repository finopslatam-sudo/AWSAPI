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
from src.aws.cost_explorer_service import CostExplorerService
from src.services.client_dashboard_service import ClientDashboardService

class ClientDashboardFacade:

    @staticmethod
    def get_summary(client_id: int, aws_account_id: int | None = None):

        # =====================================================
        # FINDINGS STATS (Delegado al servicio optimizado)
        # =====================================================
        findings_stats = ClientFindingsService.get_stats(
            client_id,
            aws_account_id
        )

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
        )

        if aws_account_id is not None:
            accounts_data = accounts_data.filter(
                AWSAccount.id == aws_account_id
            )

        accounts_data = accounts_data.first()

        accounts_count = accounts_data.accounts_count if accounts_data else 0
        last_sync = (
            accounts_data.last_sync.isoformat()
            if accounts_data and accounts_data.last_sync
            else None
        )

        # =====================================================
        # RESOURCES AFFECTED (solo inventory activo)
        # =====================================================
        resources_query = (
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
        )

        # =====================================================
        # ACCOUNT FILTER
        # =====================================================

        if aws_account_id is not None:
            resources_query = resources_query.filter(
                AWSFinding.aws_account_id == aws_account_id
            )

        resources_affected = resources_query.scalar() or 0

        # =====================================================
        # SERVICES SCANNED (Inventory real activo)
        # =====================================================

        inventory_query = db.session.query(
            AWSResourceInventory.service_name,
            func.count(AWSResourceInventory.id).label("total_resources")
        ).filter(
            AWSResourceInventory.client_id == client_id,
            AWSResourceInventory.is_active.is_(True)
        )

        # =====================================================
        # ACCOUNT FILTER
        # =====================================================

        if aws_account_id is not None:
            inventory_query = inventory_query.filter(
                AWSResourceInventory.aws_account_id == aws_account_id
            )

        services_scanned_raw = (
            inventory_query
            .group_by(AWSResourceInventory.service_name)
            .all()
        )

        services_scanned = [
            {
                "service": s.service_name,
                "total_resources": s.total_resources
            }
            for s in services_scanned_raw
        ]

        # =====================================================
        # DELEGATED SERVICES
        # =====================================================
        governance = GovernanceService.get_governance_score(
            client_id,
            aws_account_id
        )
        risk = RiskService.get_risk_score(client_id, aws_account_id)
        risk_by_service = RiskService.get_risk_breakdown_by_service(
            client_id,
            aws_account_id
        )
        priority_services = RiskService.get_priority_services(
            client_id,
            aws_account_id
        )
        executive_summary = ExecutiveService.get_executive_summary(
            client_id,
            aws_account_id
        )
        roi_projection = ROIService.get_roi_projection(
            client_id,
            aws_account_id
        )
        trend = TrendService.get_risk_trend(client_id, 30)
        remediation = RemediationService.get_remediation_metrics(
            client_id,
            30,
            aws_account_id
        )
        cost_data = ClientDashboardService.get_cost_data(
            client_id,
            aws_account_id
        )

        return {
            "findings": findings_stats,
            "accounts": accounts_count,
            "last_sync": last_sync,
            "resources_affected": resources_affected,
            "services_scanned": services_scanned,
            "governance": governance,
            "risk": risk,
            "risk_by_service": risk_by_service,
            "priority_services": priority_services,
            "executive_summary": executive_summary,
            "roi_projection": roi_projection,
            "trend": trend,
            "remediation": remediation,
            "cost": cost_data,
            
        }

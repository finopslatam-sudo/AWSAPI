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
from src.aws.cost_explorer_service import CostExplorerService #este

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

        accounts_count = accounts_data.accounts_count if accounts_data else 0
        last_sync = (
            accounts_data.last_sync.isoformat()
            if accounts_data and accounts_data.last_sync
            else None
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
        cost_data = ClientDashboardFacade._get_cost_data(client_id) #este

        return {
            "findings": findings_stats,
            "accounts": accounts_count,
            "last_sync": last_sync,
            "resources_affected": resources_affected,
            "governance": governance,
            "risk": risk,
            "risk_by_service": risk_by_service,
            "priority_services": priority_services,
            "executive_summary": executive_summary,
            "roi_projection": roi_projection,
            "trend": trend,
            "remediation": remediation,
            "cost": cost_data, #estee
        }
    @staticmethod #y de aqui al final
    def _get_cost_data(client_id: int):

        aws_account = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).first()

        if not aws_account:
            return {
                "monthly_cost": [],
                "service_breakdown": [],
                "current_month_cost": 0.0,
                "potential_savings": 0.0,
                "savings_percentage": 0.0
            }

        ce = CostExplorerService(aws_account)

        monthly_cost_raw = ce.get_last_6_months_cost()

        monthly_cost = []
        for item in monthly_cost_raw:
            amount = float(item["amount"])
            if abs(amount) < 0.01:
                amount = 0.0

            monthly_cost.append({
                "month": item["month"],
                "amount": amount
            })

        service_breakdown = ce.get_service_breakdown_current_month()

        raw_current_month_cost = monthly_cost[-1]["amount"] if monthly_cost else 0
        current_month_cost = (
            0.0 if abs(raw_current_month_cost) < 0.01
            else float(raw_current_month_cost)
        )

        savings = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        savings = float(savings)

        savings_percentage = (
            0.0 if current_month_cost <= 0
            else round((savings / current_month_cost) * 100, 2)
        )

        return {
            "monthly_cost": monthly_cost,
            "service_breakdown": service_breakdown,
            "current_month_cost": float(current_month_cost),
            "potential_savings": float(savings),
            "savings_percentage": float(savings_percentage)
        }
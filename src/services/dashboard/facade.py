from src.services.dashboard.risk_service import RiskService
from src.services.dashboard.governance_service import GovernanceService
from src.services.dashboard.executive_service import ExecutiveService
from src.services.dashboard.roi_service import ROIService
from src.services.dashboard.trend_service import TrendService
from src.services.dashboard.remediation_service import RemediationService
from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount
from src.models.database import db
from sqlalchemy import func


class ClientDashboardFacade:

    @staticmethod
    def get_summary(client_id: int):

        base_query = AWSFinding.query.filter_by(client_id=client_id)

        total = base_query.count()
        active = base_query.filter_by(resolved=False).count()
        resolved = base_query.filter_by(resolved=True).count()

        high = base_query.filter_by(severity="HIGH", resolved=False).count()
        medium = base_query.filter_by(severity="MEDIUM", resolved=False).count()
        low = base_query.filter_by(severity="LOW", resolved=False).count()

        savings = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        accounts_count = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).count()

        last_sync = db.session.query(
            func.max(AWSAccount.last_sync)
        ).filter_by(
            client_id=client_id,
            is_active=True
        ).scalar()

        resources_affected = db.session.query(
            func.count(func.distinct(AWSFinding.resource_id))
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        governance = GovernanceService.get_governance_score(client_id)
        risk = RiskService.get_risk_score(client_id)
        risk_by_service = RiskService.get_risk_breakdown_by_service(client_id)
        priority_services = RiskService.get_priority_services(client_id)
        executive_summary = ExecutiveService.get_executive_summary(client_id)
        roi_projection = ROIService.get_roi_projection(client_id)
        trend = TrendService.get_risk_trend(client_id, 30)
        remediation = RemediationService.get_remediation_metrics(client_id, 30)

        return {
            "findings": {
                "total": total,
                "active": active,
                "resolved": resolved,
                "high": high,
                "medium": medium,
                "low": low,
                "estimated_monthly_savings": float(savings)
            },
            "accounts": accounts_count,
            "last_sync": last_sync.isoformat() if last_sync else None,
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
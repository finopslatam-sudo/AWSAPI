from sqlalchemy import func
from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount
from src.models.database import db
from src.aws.cost_explorer_service import CostExplorerService

class ClientDashboardService:

    @staticmethod
    def get_summary(client_id: int):

        # ---------------- FINDINGS STATS ----------------
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

        # ---------------- AWS ACCOUNTS ----------------
        accounts_count = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).count()

        # ---------------- LAST SYNC ----------------
        last_sync = db.session.query(
            func.max(AWSAccount.last_sync)
        ).filter_by(
            client_id=client_id,
            is_active=True
        ).scalar()

        # ---------------- RESOURCES AFFECTED ----------------
        resources_affected = db.session.query(
            func.count(func.distinct(AWSFinding.resource_id))
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

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
            "resources_affected": resources_affected
        }
    @staticmethod
    def get_cost_data(client_id: int):

        aws_account = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).first()

        if not aws_account:
            return {
                "monthly_cost": [],
                "service_breakdown": [],
                "current_month_cost": 0,
                "potential_savings": 0,
                "savings_percentage": 0
            }

        ce = CostExplorerService(aws_account)

        monthly_cost = ce.get_last_6_months_cost()
        service_breakdown = ce.get_service_breakdown_current_month()

        raw_current_month_cost = monthly_cost[-1]["amount"] if monthly_cost else 0

        # Normalización financiera (evita residuos flotantes AWS)
        current_month_cost = 0 if abs(raw_current_month_cost) < 0.01 else float(raw_current_month_cost)

        # Obtener ahorro potencial desde findings
        savings = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        if current_month_cost <= 0:
            savings_percentage = 0
        else:
            savings_percentage = round((float(savings) / current_month_cost) * 100, 2)

        return {
            "monthly_cost": monthly_cost,
            "service_breakdown": service_breakdown,
            "current_month_cost": float(current_month_cost),
            "potential_savings": float(savings),
            "savings_percentage": round(savings_percentage, 2)
        }

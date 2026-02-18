from sqlalchemy import func
from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount
from src.models.database import db


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

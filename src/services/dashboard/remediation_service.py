from datetime import datetime, timedelta
from sqlalchemy import func, case, and_
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db


class RemediationService:

    # =====================================================
    # REMEDIATION TRACKING (ENTERPRISE READY)
    # =====================================================
    @staticmethod
    def get_remediation_metrics(
        client_id: int,
        days: int = 30,
        aws_account_id: int | None = None
    ):

        cutoff = datetime.utcnow() - timedelta(days=days)

        # -----------------------------------------------------
        # AGGREGATED RESOLUTION METRICS (JOIN INVENTORY ACTIVO)
        # -----------------------------------------------------
        results_query = (
            db.session.query(
                func.count(AWSFinding.id).label("total_resolved"),
                func.sum(
                    case((AWSFinding.severity == "HIGH", 1), else_=0)
                ).label("high"),
                func.sum(
                    case((AWSFinding.severity == "MEDIUM", 1), else_=0)
                ).label("medium"),
                func.sum(
                    case((AWSFinding.severity == "LOW", 1), else_=0)
                ).label("low"),
                func.sum(AWSFinding.estimated_monthly_savings).label("savings")
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
                AWSFinding.resolved.is_(True),
                AWSFinding.resolved_at >= cutoff,
                AWSResourceInventory.is_active.is_(True)
            )
        )

        if aws_account_id is not None:
            results_query = results_query.filter(
                AWSFinding.aws_account_id == aws_account_id,
                AWSResourceInventory.aws_account_id == aws_account_id
            )

        results = results_query.first()

        total_resolved = results.total_resolved or 0
        high = results.high or 0
        medium = results.medium or 0
        low = results.low or 0
        realized_savings = float(results.savings or 0)

        # -----------------------------------------------------
        # EXECUTION VELOCITY (PER DAY)
        # -----------------------------------------------------
        daily_velocity = round(total_resolved / days, 2) if days > 0 else 0

        # -----------------------------------------------------
        # FINANCIAL IMPACT
        # -----------------------------------------------------
        monthly_realized = round(realized_savings, 2)
        annual_realized = round(realized_savings * 12, 2)

        return {
            "period_days": days,
            "total_resolved": total_resolved,
            "daily_resolution_rate": daily_velocity,
            "realized_savings_monthly": monthly_realized,
            "realized_savings_annual": annual_realized,
            "by_severity": {
                "high": high,
                "medium": medium,
                "low": low
            }
        }

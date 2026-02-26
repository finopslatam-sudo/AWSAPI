from datetime import datetime, timedelta
from src.models.risk_snapshot import RiskSnapshot
from src.models.database import db


class TrendService:

    # =====================================================
    # HISTORICAL TREND (ENTERPRISE READY)
    # =====================================================
    @staticmethod
    def get_risk_trend(client_id: int, days: int = 30):

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        snapshots = (
            db.session.query(
                RiskSnapshot.created_at,
                RiskSnapshot.health_score,
                RiskSnapshot.risk_level,
                RiskSnapshot.governance_percentage,
                RiskSnapshot.financial_exposure,
                RiskSnapshot.total_findings
            )
            .filter(
                RiskSnapshot.client_id == client_id,
                RiskSnapshot.created_at >= cutoff_date
            )
            .order_by(RiskSnapshot.created_at.asc())
            .all()
        )

        trend = []

        for snap in snapshots:
            trend.append({
                "date": snap.created_at.date().isoformat(),
                "health_score": snap.health_score,
                "risk_level": snap.risk_level,
                "governance_percentage": float(snap.governance_percentage),
                "financial_exposure": float(snap.financial_exposure),
                "total_findings": snap.total_findings
            })

        # -----------------------------------------------------
        # TREND SUMMARY (EXECUTIVE INSIGHT)
        # -----------------------------------------------------
        if len(trend) >= 2:
            first_score = trend[0]["risk_score"]
            last_score = trend[-1]["risk_score"]

            delta = round(last_score - first_score, 2)

            if delta > 0:
                direction = "IMPROVING"
            elif delta < 0:
                direction = "DETERIORATING"
            else:
                direction = "STABLE"
        else:
            delta = 0
            direction = "INSUFFICIENT_DATA"

        return {
            "period_days": days,
            "data_points": len(trend),
            "risk_delta": delta,
            "trend_direction": direction,
            "series": trend
        }
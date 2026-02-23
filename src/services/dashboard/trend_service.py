from datetime import datetime, timedelta
from src.models.risk_snapshot import RiskSnapshot


class TrendService:

    # =====================================================
    # HISTORICAL TREND
    # =====================================================
    @staticmethod
    def get_risk_trend(client_id: int, days: int = 30):

        from src.models.risk_snapshot import RiskSnapshot
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        snapshots = RiskSnapshot.query.filter(
            RiskSnapshot.client_id == client_id,
            RiskSnapshot.created_at >= cutoff_date
        ).order_by(
            RiskSnapshot.created_at.asc()
        ).all()

        trend = []

        for snap in snapshots:
            trend.append({
                "date": snap.created_at.date().isoformat(),
                "risk_score": float(snap.risk_score),
                "risk_level": snap.risk_level,
                "governance_percentage": float(snap.governance_percentage),
                "financial_exposure": float(snap.financial_exposure),
                "total_findings": snap.total_findings
            })

        return trend
    
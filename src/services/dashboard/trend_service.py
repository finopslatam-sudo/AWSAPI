from src.models.risk_snapshot import RiskSnapshot
from src.models.database import db
from datetime import datetime, timedelta


class TrendService:

    @staticmethod
    def get_risk_trend(client_id: int, days: int):

        since_date = datetime.utcnow() - timedelta(days=days)

        snapshots = (
            db.session.query(
                RiskSnapshot.created_at,
                RiskSnapshot.risk_score
            )
            .filter(
                RiskSnapshot.client_id == client_id,
                RiskSnapshot.created_at >= since_date
            )
            .order_by(RiskSnapshot.created_at.asc())
            .all()
        )

        trend = []

        for snap in snapshots:
            trend.append({
                "date": snap.created_at.strftime("%Y-%m-%d"),
                "risk_score": float(snap.risk_score) if snap.risk_score is not None else 100.0
            })

        # 🔥 Evitar crash si no hay datos
        if not trend:
            return {
                "trend": [],
                "delta": 0
            }

        first_score = trend[0]["risk_score"]
        last_score = trend[-1]["risk_score"]

        delta = round(last_score - first_score, 2)

        return {
            "trend": trend,
            "delta": delta
        }
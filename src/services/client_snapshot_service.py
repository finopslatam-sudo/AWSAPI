from sqlalchemy import desc
from src.models.risk_snapshot import RiskSnapshot
from src.models.database import db


class ClientSnapshotService:

    # =====================================================
    # GET LATEST SNAPSHOT
    # =====================================================
    @staticmethod
    def get_latest_snapshot(client_id: int):

        snapshot = (
            RiskSnapshot.query
            .filter_by(client_id=client_id)
            .order_by(desc(RiskSnapshot.created_at))
            .first()
        )

        if not snapshot:
            return None

        return ClientSnapshotService._serialize(snapshot)

    # =====================================================
    # GET SNAPSHOT HISTORY (PAGINATED)
    # =====================================================
    @staticmethod
    def list_snapshots(
        client_id: int,
        page: int = 1,
        per_page: int = 30
    ):

        pagination = (
            RiskSnapshot.query
            .filter_by(client_id=client_id)
            .order_by(desc(RiskSnapshot.created_at))
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        return {
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": pagination.page,
            "per_page": pagination.per_page,
            "data": [
                ClientSnapshotService._serialize(s)
                for s in pagination.items
            ]
        }

    # =====================================================
    # GET TREND (LAST N DAYS)
    # =====================================================
    @staticmethod
    def get_trend(client_id: int, days: int = 30):

        snapshots = (
            RiskSnapshot.query
            .filter_by(client_id=client_id)
            .order_by(RiskSnapshot.created_at.asc())
            .all()
        )

        if not snapshots:
            return []

        # Filtrar manualmente últimos N días
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)

        filtered = [
            s for s in snapshots
            if s.created_at >= cutoff
        ]

        return [
            {
                "date": s.created_at.date().isoformat(),
                "risk_score": float(s.risk_score),
                "risk_level": s.risk_level,
                "governance_percentage": float(s.governance_percentage),
                "financial_exposure": float(s.financial_exposure),
                "total_findings": s.total_findings,
                "total_resources": s.total_resources
            }
            for s in filtered
        ]

    # =====================================================
    # COMPARE LAST TWO SNAPSHOTS
    # =====================================================
    @staticmethod
    def get_delta(client_id: int):

        snapshots = (
            RiskSnapshot.query
            .filter_by(client_id=client_id)
            .order_by(desc(RiskSnapshot.created_at))
            .limit(2)
            .all()
        )

        if len(snapshots) < 2:
            return None

        latest = snapshots[0]
        previous = snapshots[1]

        return {
            "risk_score_delta": float(latest.risk_score) - float(previous.risk_score),
            "governance_delta": float(latest.governance_percentage) - float(previous.governance_percentage),
            "financial_exposure_delta": float(latest.financial_exposure) - float(previous.financial_exposure),
            "findings_delta": latest.total_findings - previous.total_findings
        }

    # =====================================================
    # SERIALIZER
    # =====================================================
    @staticmethod
    def _serialize(snapshot: RiskSnapshot):

        return {
            "id": snapshot.id,
            "risk_score": float(snapshot.risk_score),
            "risk_level": snapshot.risk_level,
            "governance_percentage": float(snapshot.governance_percentage),
            "total_resources": snapshot.total_resources,
            "total_findings": snapshot.total_findings,
            "financial_exposure": float(snapshot.financial_exposure),
            "created_at": snapshot.created_at.isoformat()
        }
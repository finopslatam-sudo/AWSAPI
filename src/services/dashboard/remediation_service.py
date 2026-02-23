from datetime import datetime, timedelta
from src.models.aws_finding import AWSFinding


class RemediationService:

   # =====================================================
    # REMEDIATION TRACKING
    # =====================================================
    @staticmethod
    def get_remediation_metrics(client_id: int, days: int = 30):

        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Findings resueltos en el período
        resolved_findings = AWSFinding.query.filter(
            AWSFinding.client_id == client_id,
            AWSFinding.resolved == True,
            AWSFinding.resolved_at >= cutoff
        ).all()

        total_resolved = len(resolved_findings)

        # Ahorro materializado
        realized_savings = sum(
            float(f.estimated_monthly_savings or 0)
            for f in resolved_findings
        )

        # Resueltos por severidad
        high = len([f for f in resolved_findings if f.severity == "HIGH"])
        medium = len([f for f in resolved_findings if f.severity == "MEDIUM"])
        low = len([f for f in resolved_findings if f.severity == "LOW"])

        return {
            "period_days": days,
            "total_resolved": total_resolved,
            "realized_savings": round(realized_savings, 2),
            "by_severity": {
                "high": high,
                "medium": medium,
                "low": low
            }
        }
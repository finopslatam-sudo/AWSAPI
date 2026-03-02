from src.models.aws_finding import AWSFinding
from src.models.database import db


class RightsizingService:

    @staticmethod
    def get_rightsizing_recommendations(client_id: int):

        findings = (
            AWSFinding.query
            .filter(
                AWSFinding.client_id == client_id,
                AWSFinding.resolved.is_(False),
                AWSFinding.finding_type.in_([
                    "EC2_UNDERUTILIZED",
                    "RDS_UNDERUTILIZED"
                ])
            )
            .all()
        )

        results = []
        total_savings = 0

        for f in findings:

            savings = float(f.estimated_monthly_savings or 0)
            total_savings += savings

            results.append({
                "resource_id": f.resource_id,
                "resource_type": f.resource_type,
                "service": f.resource_type,
                "message": f.message,
                "estimated_monthly_savings": savings,
                "created_at": f.created_at.isoformat()
            })

        return {
            "total_recommendations": len(results),
            "total_estimated_monthly_savings": round(total_savings, 2),
            "recommendations": results
        }
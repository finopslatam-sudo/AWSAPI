from src.models.aws_finding import AWSFinding


class RightsizingService:

    SUPPORTED_TYPES = [
        "EC2_UNDERUTILIZED",
        "RDS_UNDERUTILIZED"
    ]

    @staticmethod
    def get_rightsizing_recommendations(client_id: int):

        findings = (
            AWSFinding.query
            .filter(
                AWSFinding.client_id == client_id,
                AWSFinding.resolved.is_(False),
                AWSFinding.finding_type.in_(
                    RightsizingService.SUPPORTED_TYPES
                )
            )
            .order_by(AWSFinding.created_at.desc())
            .all()
        )

        results = []
        total_savings = 0.0

        for f in findings:

            savings = float(f.estimated_monthly_savings or 0)
            total_savings += savings

            results.append({
                "id": f.id,
                "resource_id": f.resource_id,
                "resource_type": f.resource_type,
                "finding_type": f.finding_type,
                "severity": f.severity,
                "message": f.message,
                "estimated_monthly_savings": round(savings, 2),
                "created_at": f.created_at.isoformat()
            })

        return {
            "supported_services": ["EC2", "RDS"],
            "total_recommendations": len(results),
            "total_estimated_monthly_savings": round(total_savings, 2),
            "has_data": len(results) > 0,
            "recommendations": results
        }
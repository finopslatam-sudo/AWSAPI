from src.models.aws_finding import AWSFinding


class RightsizingService:

    SUPPORTED_TYPES = [
        "RIGHTSIZING_OPPORTUNITY",
        "EC2_UNDERUTILIZED",
        "RDS_UNDERUTILIZED",
        "EBS_GP2_TO_GP3",
        "LAMBDA_MEMORY_RIGHTSIZING",
        "DYNAMODB_PROVISIONED_RIGHTSIZING",
        "CLOUDWATCH_STORAGE_RIGHTSIZING",
        "NAT_IDLE_GATEWAY",
        "REDSHIFT_UNDERUTILIZED"
    ]

    @staticmethod
    def get_rightsizing_recommendations(
        client_id: int,
        aws_account_id: int | None = None
    ):

        query = (
            AWSFinding.query
            .filter(
                AWSFinding.client_id == client_id,
                AWSFinding.resolved.is_(False),
                AWSFinding.finding_type.in_(
                    RightsizingService.SUPPORTED_TYPES
                )
            )
        )

        if aws_account_id is not None:
            query = query.filter(
                AWSFinding.aws_account_id == aws_account_id
            )

        findings = query.order_by(AWSFinding.created_at.desc()).all()

        results = []
        total_savings = 0.0

        for f in findings:

            savings = float(f.estimated_monthly_savings or 0)
            total_savings += savings

            results.append({
                "id": f.id,
                "resource_id": f.resource_id,
                "resource_type": f.resource_type,
                "aws_account_id": f.aws_account_id,
                "aws_service": f.aws_service,
                "finding_type": f.finding_type,
                "severity": f.severity,
                "message": f.message,
                "estimated_monthly_savings": round(savings, 2),
                "created_at": f.created_at.isoformat()
            })

        return {
            "supported_services": [
                "EC2",
                "RDS",
                "EBS",
                "Lambda",
                "DynamoDB",
                "CloudWatch",
                "NAT",
                "Redshift"
            ],
            "total_recommendations": len(results),
            "total_estimated_monthly_savings": round(total_savings, 2),
            "has_data": len(results) > 0,
            "recommendations": results
        }

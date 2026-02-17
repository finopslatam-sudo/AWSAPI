from src.models.aws_finding import AWSFinding


class ClientFindingsService:

    @staticmethod
    def list_findings(client_id, status=None, severity=None, finding_type=None):

        query = AWSFinding.query.filter_by(client_id=client_id)

        if status == "active":
            query = query.filter_by(resolved=False)

        if status == "resolved":
            query = query.filter_by(resolved=True)

        if severity:
            query = query.filter_by(severity=severity)

        if finding_type:
            query = query.filter_by(finding_type=finding_type)

        findings = query.order_by(AWSFinding.created_at.desc()).all()

        return [
            {
                "id": f.id,
                "resource_id": f.resource_id,
                "resource_type": f.resource_type,
                "finding_type": f.finding_type,
                "severity": f.severity,
                "message": f.message,
                "estimated_monthly_savings": float(f.estimated_monthly_savings),
                "resolved": f.resolved,
                "detected_at": f.detected_at.isoformat(),
                "created_at": f.created_at.isoformat()
            }
            for f in findings
        ]

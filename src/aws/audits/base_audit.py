from src.models.aws_finding import AWSFinding
from src.models.database import db
from datetime import datetime


class BaseAudit:
    """
    Clase base para auditorías FinOps.
    Maneja:
    - Anti-duplicados
    - Reapertura automática
    - Resolución automática
    """

    def __init__(self, boto_session, client_id, aws_account):
        self.session = boto_session
        self.client_id = client_id
        self.aws_account = aws_account

    def run(self):
        raise NotImplementedError("Audit must implement run()")

    # ---------------------------------------------------------
    # CREATE OR REOPEN FINDING
    # ---------------------------------------------------------
    def create_or_reopen_finding(
        self,
        resource_id,
        resource_type,
        finding_type,
        severity,
        message,
        estimated_monthly_savings=0
    ):
        existing = AWSFinding.query.filter_by(
            aws_account_id=self.aws_account.id,
            resource_id=resource_id,
            finding_type=finding_type
        ).first()

        # Caso 1: existe y está activo → no hacer nada
        if existing and not existing.resolved:
            return False

        # Caso 2: existe pero estaba resuelto → reabrir
        if existing and existing.resolved:
            existing.resolved = False
            existing.resolved_at = None
            existing.severity = severity
            existing.message = message
            existing.estimated_monthly_savings = estimated_monthly_savings
            return True

        # Caso 3: no existe → crear nuevo
        finding = AWSFinding(
            client_id=self.client_id,
            aws_account_id=self.aws_account.id,
            resource_id=resource_id,
            resource_type=resource_type,
            finding_type=finding_type,
            severity=severity,
            message=message,
            estimated_monthly_savings=estimated_monthly_savings
        )

        db.session.add(finding)
        return True

    # ---------------------------------------------------------
    # AUTO RESOLVE FINDINGS QUE YA NO EXISTEN
    # ---------------------------------------------------------
    def resolve_missing_findings(self, active_resource_ids, finding_type):
        """
        Marca como resueltos los findings que ya no aplican.
        """

        findings = AWSFinding.query.filter_by(
            aws_account_id=self.aws_account.id,
            finding_type=finding_type,
            resolved=False
        ).all()

        for f in findings:
            if f.resource_id not in active_resource_ids:
                f.resolved = True
                f.resolved_at = datetime.utcnow()

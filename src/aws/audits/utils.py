from src.models.aws_finding import AWSFinding
from src.models.database import db


def create_finding_if_not_exists(
    client_id,
    aws_account_id,
    resource_id,
    resource_type,
    finding_type,
    severity,
    message,
    estimated_savings=0
):
    """
    Crea un finding solo si no existe uno activo igual.
    Retorna True si fue creado.
    Retorna False si ya existía.
    """

    existing = AWSFinding.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account_id,
        resource_id=resource_id,
        finding_type=finding_type,
        resolved=False
    ).first()

    if existing:
        return False

    finding = AWSFinding(
        client_id=client_id,
        aws_account_id=aws_account_id,
        resource_id=resource_id,
        resource_type=resource_type,
        finding_type=finding_type,
        severity=severity,
        message=message,
        estimated_monthly_savings=estimated_savings
    )

    db.session.add(finding)
    return True

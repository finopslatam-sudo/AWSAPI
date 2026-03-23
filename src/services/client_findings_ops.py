"""Operaciones auxiliares para findings (separado para mantener <300 líneas)."""

from datetime import datetime

from sqlalchemy import func, case, and_

from src.models.database import db
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory


def resolve_finding_record(client_id: int, finding_id: int, user_id: int):
    finding = (
        db.session.query(AWSFinding)
        .filter(
            AWSFinding.id == finding_id,
            AWSFinding.client_id == client_id
        )
        .first()
    )

    if not finding:
        return None

    if finding.resolved:
        return finding

    finding.resolved = True
    finding.resolved_at = datetime.utcnow()
    finding.resolved_by = user_id
    finding.updated_at = datetime.utcnow()

    db.session.commit()

    return finding


def get_summary_by_service(client_id: int):

    results = (
        db.session.query(
            AWSFinding.aws_service,
            func.count(AWSFinding.id).label("total"),
            func.sum(
                case((AWSFinding.severity == "HIGH", 1), else_=0)
            ).label("high"),
            func.sum(
                case((AWSFinding.severity == "MEDIUM", 1), else_=0)
            ).label("medium"),
            func.sum(
                case((AWSFinding.severity == "LOW", 1), else_=0)
            ).label("low"),
        )
        .join(
            AWSResourceInventory,
            and_(
                AWSFinding.resource_id == AWSResourceInventory.resource_id,
                AWSFinding.client_id == AWSResourceInventory.client_id,
            )
        )
        .filter(
            AWSFinding.client_id == client_id,
            AWSFinding.resolved.is_(False),
            AWSResourceInventory.is_active.is_(True)
        )
        .group_by(AWSFinding.aws_service)
        .all()
    )

    return [
        {
            "service": r.aws_service,
            "total": r.total or 0,
            "high": r.high or 0,
            "medium": r.medium or 0,
            "low": r.low or 0
        }
        for r in results
    ]


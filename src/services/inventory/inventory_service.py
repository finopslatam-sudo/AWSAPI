from sqlalchemy import func, case, and_

from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


def _compute_health_score(high: int, medium: int, low: int, total_resources: int) -> tuple:
    """Returns (health_score, risk_level)."""
    risk_points = (high * 10) + (medium * 5) + (low * 2)
    if total_resources > 0:
        health_score = max(0, 100 - (risk_points / total_resources * 10))
    else:
        health_score = 100
    health_score = round(health_score)
    risk_level = "LOW" if health_score >= 85 else ("MEDIUM" if health_score >= 60 else "HIGH")
    return health_score, risk_level


class InventoryService:

    @staticmethod
    def get_services_summary(client_id):
        severity_rank = case(
            (AWSFinding.severity == "LOW", 1),
            (AWSFinding.severity == "MEDIUM", 2),
            (AWSFinding.severity == "HIGH", 3),
            else_=0
        )

        findings_subq = (
            db.session.query(
                AWSFinding.resource_id.label("f_resource_id"),
                func.count(AWSFinding.id).label("f_total"),
                func.sum(case((AWSFinding.severity == "HIGH", 1), else_=0)).label("f_high"),
                func.sum(case((AWSFinding.severity == "MEDIUM", 1), else_=0)).label("f_medium"),
                func.sum(case((AWSFinding.severity == "LOW", 1), else_=0)).label("f_low"),
                func.max(severity_rank).label("f_max_severity_rank"),
            )
            .filter(AWSFinding.client_id == client_id, AWSFinding.resolved == False)
            .group_by(AWSFinding.resource_id)
            .subquery()
        )

        query = (
            db.session.query(
                AWSResourceInventory.service_name.label("service"),
                func.count(func.distinct(AWSResourceInventory.id)).label("total_resources"),
                func.coalesce(func.sum(findings_subq.c.f_total), 0).label("total_findings"),
                func.coalesce(func.sum(findings_subq.c.f_high), 0).label("high_count"),
                func.coalesce(func.sum(findings_subq.c.f_medium), 0).label("medium_count"),
                func.coalesce(func.sum(findings_subq.c.f_low), 0).label("low_count"),
                func.max(findings_subq.c.f_max_severity_rank).label("max_severity_rank"),
            )
            .outerjoin(
                findings_subq,
                findings_subq.c.f_resource_id == AWSResourceInventory.resource_id
            )
            .filter(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.is_active == True
            )
            .group_by(AWSResourceInventory.service_name)
        )

        data = []
        for r in query.all():
            total_resources = int(r.total_resources or 0)
            high = int(r.high_count or 0)
            medium = int(r.medium_count or 0)
            low = int(r.low_count or 0)
            health_score, risk_level = _compute_health_score(high, medium, low, total_resources)
            data.append({
                "service": r.service,
                "total_resources": total_resources,
                "total_findings": int(r.total_findings or 0),
                "high": high,
                "medium": medium,
                "low": low,
                "health_score": health_score,
                "risk_level": risk_level,
            })
        return data

    @staticmethod
    def get_global_health_score(client_id):
        query = (
            db.session.query(
                func.count(func.distinct(AWSResourceInventory.id)).label("total_resources"),
                func.sum(case((AWSFinding.severity == "HIGH", 1), else_=0)).label("high_count"),
                func.sum(case((AWSFinding.severity == "MEDIUM", 1), else_=0)).label("medium_count"),
                func.sum(case((AWSFinding.severity == "LOW", 1), else_=0)).label("low_count"),
                func.count(AWSFinding.id).label("total_findings"),
            )
            .outerjoin(
                AWSFinding,
                and_(
                    AWSFinding.resource_id == AWSResourceInventory.resource_id,
                    AWSFinding.client_id == client_id,
                    AWSFinding.resolved == False
                )
            )
            .filter(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.is_active == True
            )
        )

        result = query.one()
        total_resources = result.total_resources or 0
        high = result.high_count or 0
        medium = result.medium_count or 0
        low = result.low_count or 0
        health_score, risk_level = _compute_health_score(high, medium, low, total_resources)

        return {
            "health_score": health_score,
            "risk_level": risk_level,
            "total_resources": total_resources,
            "total_findings": result.total_findings or 0,
            "high": high,
            "medium": medium,
            "low": low,
        }

from sqlalchemy import func, case, and_
from datetime import datetime

from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class InventoryResourcesService:

    @staticmethod
    def get_resources_by_service(
        client_id,
        service_name,
        min_severity=None,
        sort="risk_desc",
        page=1,
        per_page=50
    ):
        severity_rank = case(
            (AWSFinding.severity == "LOW", 1),
            (AWSFinding.severity == "MEDIUM", 2),
            (AWSFinding.severity == "HIGH", 3),
            else_=0
        )

        base_query = (
            db.session.query(
                AWSResourceInventory.resource_id,
                AWSResourceInventory.resource_type,
                AWSResourceInventory.region,
                AWSResourceInventory.state,
                AWSResourceInventory.detected_at,
                func.count(AWSFinding.id).label("findings_count"),
                func.max(severity_rank).label("max_severity_rank"),
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
                AWSResourceInventory.is_active == True,
                AWSResourceInventory.service_name == service_name
            )
            .group_by(
                AWSResourceInventory.resource_id,
                AWSResourceInventory.resource_type,
                AWSResourceInventory.region,
                AWSResourceInventory.state,
                AWSResourceInventory.detected_at
            )
        )

        severity_map = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        if min_severity and min_severity in severity_map:
            base_query = base_query.having(
                func.max(severity_rank) >= severity_map[min_severity]
            )

        if sort == "risk_desc":
            base_query = base_query.order_by(
                func.max(severity_rank).desc(),
                func.count(AWSFinding.id).desc()
            )
        elif sort == "risk_asc":
            base_query = base_query.order_by(
                func.max(severity_rank).asc(),
                func.count(AWSFinding.id).asc()
            )
        elif sort == "aging_desc":
            base_query = base_query.order_by(AWSResourceInventory.detected_at.asc())
        else:
            base_query = base_query.order_by(func.max(severity_rank).desc())

        per_page = min(max(per_page, 1), 200)
        pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)

        now = datetime.utcnow()
        data = []
        for r in pagination.items:
            aging_days = (now - r.detected_at).days if r.detected_at else 0
            risk_score = (r.max_severity_rank or 0) * (r.findings_count or 0)
            data.append({
                "resource_id": r.resource_id,
                "resource_type": r.resource_type,
                "region": r.region,
                "state": r.state,
                "findings_count": r.findings_count or 0,
                "max_severity": (
                    "LOW" if r.max_severity_rank == 1 else
                    "MEDIUM" if r.max_severity_rank == 2 else
                    "HIGH" if r.max_severity_rank == 3 else
                    None
                ),
                "aging_days": aging_days,
                "risk_score": risk_score,
            })

        return {
            "items": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            },
        }

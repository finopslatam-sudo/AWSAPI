from sqlalchemy import func, or_
from src.models.aws_finding import AWSFinding
from src.models.database import db
from datetime import datetime

class ClientFindingsService:

    @staticmethod
    def list_findings(
        client_id,
        status=None,
        severity=None,
        finding_type=None,
        page=1,
        per_page=20,
        search=None,
        sort_by="created_at",
        sort_order="desc"
    ):

        query = AWSFinding.query.filter_by(client_id=client_id)

        # ---------------- STATUS FILTER ----------------
        if status == "active":
            query = query.filter_by(resolved=False)

        elif status == "resolved":
            query = query.filter_by(resolved=True)

        # ---------------- SEVERITY FILTER ----------------
        if severity:
            query = query.filter_by(severity=severity)

        # ---------------- FINDING TYPE FILTER ----------------
        if finding_type:
            query = query.filter_by(finding_type=finding_type)

        # ---------------- SEARCH FILTER ----------------
        if search:
            query = query.filter(
                or_(
                    AWSFinding.resource_id.ilike(f"%{search}%"),
                    AWSFinding.message.ilike(f"%{search}%")
                )
            )

        # ---------------- SORTING (SAFE) ----------------
        allowed_sort_fields = [
            "created_at",
            "detected_at",
            "severity",
            "estimated_monthly_savings",
            "resource_id"
        ]

        if sort_by not in allowed_sort_fields:
            sort_by = "created_at"

        sort_column = getattr(AWSFinding, sort_by)

        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # ---------------- PAGINATION ----------------
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        findings = pagination.items

        return {
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": pagination.page,
            "per_page": pagination.per_page,
            "data": [
                {
                    "id": f.id,
                    "resource_id": f.resource_id,
                    "resource_type": f.resource_type,
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "message": f.message,
                    "estimated_monthly_savings": float(f.estimated_monthly_savings or 0),
                    "resolved": f.resolved,
                    "detected_at": f.detected_at.isoformat() if f.detected_at else None,
                    "created_at": f.created_at.isoformat() if f.created_at else None
                }
                for f in findings
            ]
        }

    @staticmethod
    def get_stats(client_id):

        base_query = AWSFinding.query.filter_by(client_id=client_id)

        total = base_query.count()
        active = base_query.filter_by(resolved=False).count()
        resolved = base_query.filter_by(resolved=True).count()

        high = base_query.filter_by(severity="HIGH").count()
        medium = base_query.filter_by(severity="MEDIUM").count()
        low = base_query.filter_by(severity="LOW").count()

        savings = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        return {
            "total": total,
            "active": active,
            "resolved": resolved,
            "high": high,
            "medium": medium,
            "low": low,
            "estimated_monthly_savings": float(savings)
        }

    @staticmethod
    def resolve_finding(client_id, finding_id, user_id):

        finding = AWSFinding.query.filter_by(
            id=finding_id,
            client_id=client_id
        ).first()

        if not finding:
            return None

        if finding.resolved:
            return finding

        finding.resolved = True
        finding.resolved_at = datetime.utcnow()
        finding.resolved_by = user_id

        db.session.commit()

        return finding


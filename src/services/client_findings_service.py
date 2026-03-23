from sqlalchemy import func, case, and_
from datetime import datetime

from src.models.database import db
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_account import AWSAccount
from src.services.client_dashboard_service import ClientDashboardService

# Filter/query helpers live in a dedicated module to keep this file < 300 lines.
from src.services.client_findings_filters import (
    apply_common_filters,
    build_savings_subquery,
)


class ClientFindingsService:

    # =====================================================
    # LIST FINDINGS (ENTERPRISE READY)
    # =====================================================
    @staticmethod
    def list_findings(
        client_id,
        aws_account_id=None,
        status=None,
        severity=None,
        finding_type=None,
        service=None,
        region=None,
        page=1,
        per_page=20,
        search=None,
        sort_by="created_at",
        sort_order="desc"
    ):

        # ---------------- BASE QUERY (JOIN INVENTORY ACTIVO) ----------------
        query = (
            db.session.query(
                AWSFinding,
                AWSAccount.account_name,
                AWSAccount.account_id
            )
            .join(
                AWSResourceInventory,
                and_(
                    AWSFinding.resource_id == AWSResourceInventory.resource_id,
                    AWSFinding.client_id == AWSResourceInventory.client_id
                )
            )
            .join(
                AWSAccount,
                AWSFinding.aws_account_id == AWSAccount.id
            )
            .filter(
                AWSFinding.client_id == client_id,
                AWSResourceInventory.is_active.is_(True)
            )
        )

        query = apply_common_filters(
            query,
            aws_account_id=aws_account_id,
            status=status,
            severity=severity,
            finding_type=finding_type,
            service=service,
            search=search,
            region=region
        )

        # ---------------- SAFE SORTING ----------------
        allowed_sort_fields = {
            "created_at": AWSFinding.created_at,
            "detected_at": AWSFinding.detected_at,
            "severity": AWSFinding.severity,
            "estimated_monthly_savings": AWSFinding.estimated_monthly_savings,
            "resource_id": AWSFinding.resource_id
        }

        sort_column = allowed_sort_fields.get(sort_by, AWSFinding.created_at)

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
                    "aws_account_id": f.aws_account_id,
                    "aws_account_name": account_name,
                    "aws_account_number": account_number,

                    "resource_id": f.resource_id,
                    "resource_type": f.resource_type,
                    "region": f.region,
                    "aws_service": f.aws_service,
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "message": f.message,

                    "estimated_monthly_savings": float(f.estimated_monthly_savings or 0),

                    "resolved": f.resolved,

                    "detected_at": f.detected_at.isoformat() if f.detected_at else None,
                    "created_at": f.created_at.isoformat() if f.created_at else None
                }
                for f, account_name, account_number in findings
            ]
        }

    # =====================================================
    # GLOBAL STATS (1 QUERY - ENTERPRISE)
    # =====================================================
    @staticmethod
    def get_stats(
        client_id,
        aws_account_id=None,
        status=None,
        severity=None,
        finding_type=None,
        service=None,
        search=None,
        region=None
    ):

        query = (
            db.session.query(
                func.count(AWSFinding.id).label("total"),

                func.sum(
                    case((AWSFinding.resolved.is_(False), 1), else_=0)
                ).label("active"),

                func.sum(
                    case((AWSFinding.resolved.is_(True), 1), else_=0)
                ).label("resolved"),

                func.sum(
                    case((AWSFinding.severity == "HIGH", 1), else_=0)
                ).label("high"),

                func.sum(
                    case((AWSFinding.severity == "MEDIUM", 1), else_=0)
                ).label("medium"),

                func.sum(
                    case((AWSFinding.severity == "LOW", 1), else_=0)
                ).label("low"),

                func.sum(
                    case(
                        (AWSFinding.resolved.is_(False),
                         AWSFinding.estimated_monthly_savings),
                        else_=0
                    )
                ).label("savings")
            )
            .join(
                AWSResourceInventory,
                and_(
                    AWSFinding.resource_id == AWSResourceInventory.resource_id,
                    AWSFinding.client_id == AWSResourceInventory.client_id
                )
            )
            .filter(
                AWSFinding.client_id == client_id,
                AWSResourceInventory.is_active.is_(True)
            )
        )

        query = apply_common_filters(
            query,
            aws_account_id=aws_account_id,
            status=status,
            severity=severity,
            finding_type=finding_type,
            service=service,
            search=search,
            region=region
        )

        results = query.first()

        # Deduplicated savings subquery (avoids double-counting same resource)
        active_savings = build_savings_subquery(
            db,
            client_id,
            aws_account_id=aws_account_id,
            status=status,
            severity=severity,
            finding_type=finding_type,
            service=service,
            search=search,
            region=region
        )

        estimated_savings = db.session.query(
            func.sum(active_savings.c.estimated_monthly_savings)
        ).scalar() or 0

        financial_opportunities = db.session.query(
            func.count()
        ).select_from(active_savings).filter(
            active_savings.c.estimated_monthly_savings > 0
        ).scalar() or 0

        active_findings = results.active or 0
        review_recommendations = max(active_findings - financial_opportunities, 0)

        return {
            "total": results.total or 0,
            "active": active_findings,
            "resolved": results.resolved or 0,
            "high": results.high or 0,
            "medium": results.medium or 0,
            "low": results.low or 0,
            "estimated_monthly_savings": float(estimated_savings),
            "financial_opportunities": financial_opportunities,
            "review_recommendations": review_recommendations
        }

    # =====================================================
    # RESOLVE FINDING (AUDIT READY)
    # =====================================================
    @staticmethod
    def resolve_finding(client_id, finding_id, user_id):

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

    # =====================================================
    # SUMMARY BY AWS SERVICE (ENTERPRISE SAFE)
    # =====================================================
    @staticmethod
    def get_summary_by_service(client_id):

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

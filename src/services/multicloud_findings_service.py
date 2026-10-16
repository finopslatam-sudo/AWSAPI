"""
multicloud_findings_service.py
------------------------------
Servicio para consultar hallazgos y estadísticas de Azure y GCP,
unificando la respuesta con el formato consumido por el frontend.
"""

from sqlalchemy import func, case, or_
from src.models.database import db
from src.models.azure_finding import AzureFinding
from src.models.azure_account import AzureAccount
from src.models.gcp_finding import GCPFinding
from src.models.gcp_account import GCPAccount


def _query_findings(model, acc_model, acc_fk_col, client_id, account_id, status, severity, finding_type, service, svc_col, region, search):
    query = (
        db.session.query(model, acc_model)
        .join(acc_model, acc_fk_col == acc_model.id)
        .filter(model.client_id == client_id)
    )
    if account_id:
        query = query.filter(acc_fk_col == account_id)
    if status == "active":
        query = query.filter(model.resolved.is_(False))
    elif status == "resolved":
        query = query.filter(model.resolved.is_(True))
    if severity:
        query = query.filter(model.severity == severity)
    if finding_type:
        query = query.filter(model.finding_type == finding_type)
    if service:
        query = query.filter(svc_col.ilike(service))
    if region:
        query = query.filter(model.region.ilike(f"{region}%"))
    if search:
        p = f"%{search}%"
        query = query.filter(or_(model.resource_id.ilike(p), model.message.ilike(p), model.finding_type.ilike(p)))
    return query


def _query_stats(model, acc_fk_col, client_id, account_id, status, severity, finding_type, service, svc_col, region, search):
    query = db.session.query(
        func.count(model.id).label("total"),
        func.sum(case((model.resolved.is_(False), 1), else_=0)).label("active"),
        func.sum(case((model.resolved.is_(True), 1), else_=0)).label("resolved"),
        func.sum(case((model.severity == "HIGH", 1), else_=0)).label("high"),
        func.sum(case((model.severity == "MEDIUM", 1), else_=0)).label("medium"),
        func.sum(case((model.severity == "LOW", 1), else_=0)).label("low"),
        func.sum(case((model.resolved.is_(False), model.estimated_monthly_savings), else_=0)).label("savings")
    ).filter(model.client_id == client_id)

    if account_id:
        query = query.filter(acc_fk_col == account_id)
    if status == "active":
        query = query.filter(model.resolved.is_(False))
    elif status == "resolved":
        query = query.filter(model.resolved.is_(True))
    if severity:
        query = query.filter(model.severity == severity)
    if finding_type:
        query = query.filter(model.finding_type == finding_type)
    if service:
        query = query.filter(svc_col.ilike(service))
    if region:
        query = query.filter(model.region.ilike(f"{region}%"))
    if search:
        p = f"%{search}%"
        query = query.filter(or_(model.resource_id.ilike(p), model.message.ilike(p)))

    res = query.first()
    active = (res.active or 0) if res else 0
    savings = float(res.savings or 0) if res else 0.0

    opps_q = db.session.query(func.count(model.id)).filter(
        model.client_id == client_id, model.resolved.is_(False), model.estimated_monthly_savings > 0
    )
    if account_id:
        opps_q = opps_q.filter(acc_fk_col == account_id)
    opps = opps_q.scalar() or 0

    return {
        "total": (res.total or 0) if res else 0,
        "active": active,
        "resolved": (res.resolved or 0) if res else 0,
        "high": (res.high or 0) if res else 0,
        "medium": (res.medium or 0) if res else 0,
        "low": (res.low or 0) if res else 0,
        "estimated_monthly_savings": savings,
        "financial_opportunities": opps,
        "review_recommendations": max(active - opps, 0)
    }


class MultiCloudFindingsService:

    @staticmethod
    def list_azure_findings(client_id, account_id=None, status=None, severity=None, finding_type=None, service=None, region=None, page=1, per_page=20, search=None, sort_by="created_at", sort_order="desc"):
        q = _query_findings(
            AzureFinding, AzureAccount, AzureFinding.azure_account_id,
            client_id, account_id, status, severity, finding_type, service, AzureFinding.azure_service, region, search
        )
        sort_col = getattr(AzureFinding, sort_by, AzureFinding.created_at)
        q = q.order_by(sort_col.asc() if sort_order == "asc" else sort_col.desc())
        p = q.paginate(page=page, per_page=per_page, error_out=False)
        return {
            "total": p.total, "pages": p.pages, "current_page": p.page, "per_page": p.per_page,
            "data": [
                {
                    "id": f.id, "aws_account_id": f.azure_account_id,
                    "aws_account_name": acc.subscription_name, "aws_account_number": acc.subscription_id,
                    "resource_id": f.resource_id, "resource_type": f.resource_type, "region": f.region,
                    "aws_service": f.azure_service, "finding_type": f.finding_type, "severity": f.severity,
                    "message": f.message, "estimated_monthly_savings": float(f.estimated_monthly_savings or 0),
                    "resolved": f.resolved, "provider": "azure",
                    "detected_at": f.detected_at.isoformat() if f.detected_at else None,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f, acc in p.items
            ]
        }

    @staticmethod
    def get_azure_stats(client_id, account_id=None, status=None, severity=None, finding_type=None, service=None, search=None, region=None):
        return _query_stats(
            AzureFinding, AzureFinding.azure_account_id,
            client_id, account_id, status, severity, finding_type, service, AzureFinding.azure_service, region, search
        )

    @staticmethod
    def list_gcp_findings(client_id, account_id=None, status=None, severity=None, finding_type=None, service=None, region=None, page=1, per_page=20, search=None, sort_by="created_at", sort_order="desc"):
        q = _query_findings(
            GCPFinding, GCPAccount, GCPFinding.gcp_account_id,
            client_id, account_id, status, severity, finding_type, service, GCPFinding.gcp_service, region, search
        )
        sort_col = getattr(GCPFinding, sort_by, GCPFinding.created_at)
        q = q.order_by(sort_col.asc() if sort_order == "asc" else sort_col.desc())
        p = q.paginate(page=page, per_page=per_page, error_out=False)
        return {
            "total": p.total, "pages": p.pages, "current_page": p.page, "per_page": p.per_page,
            "data": [
                {
                    "id": f.id, "aws_account_id": f.gcp_account_id,
                    "aws_account_name": acc.project_name, "aws_account_number": acc.project_id,
                    "resource_id": f.resource_id, "resource_type": f.resource_type, "region": f.region,
                    "aws_service": f.gcp_service, "finding_type": f.finding_type, "severity": f.severity,
                    "message": f.message, "estimated_monthly_savings": float(f.estimated_monthly_savings or 0),
                    "resolved": f.resolved, "provider": "gcp",
                    "detected_at": f.detected_at.isoformat() if f.detected_at else None,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f, acc in p.items
            ]
        }

    @staticmethod
    def get_gcp_stats(client_id, account_id=None, status=None, severity=None, finding_type=None, service=None, search=None, region=None):
        return _query_stats(
            GCPFinding, GCPFinding.gcp_account_id,
            client_id, account_id, status, severity, finding_type, service, GCPFinding.gcp_service, region, search
        )


from sqlalchemy import func, case, and_
from datetime import datetime

from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class InventoryService:

    # ======================================================
    # SERVICES SUMMARY (ENTERPRISE SAFE - FIXED JOIN STRATEGY)
    # ======================================================
    @staticmethod
    def get_services_summary(client_id):

        # --------------------------------------------------
        # Severity ranking (used in subquery)
        # --------------------------------------------------

        severity_rank = case(
            (AWSFinding.severity == "LOW", 1),
            (AWSFinding.severity == "MEDIUM", 2),
            (AWSFinding.severity == "HIGH", 3),
            else_=0
        )

        # --------------------------------------------------
        # SUBQUERY: Aggregate findings per resource FIRST
        # --------------------------------------------------

        findings_subq = (
            db.session.query(
                AWSFinding.resource_id.label("f_resource_id"),
                func.count(AWSFinding.id).label("f_total"),
                func.sum(
                    case((AWSFinding.severity == "HIGH", 1), else_=0)
                ).label("f_high"),
                func.sum(
                    case((AWSFinding.severity == "MEDIUM", 1), else_=0)
                ).label("f_medium"),
                func.sum(
                    case((AWSFinding.severity == "LOW", 1), else_=0)
                ).label("f_low"),
                func.max(severity_rank).label("f_max_severity_rank"),
            )
            .filter(
                AWSFinding.client_id == client_id,
                AWSFinding.resolved == False
            )
            .group_by(AWSFinding.resource_id)
            .subquery()
        )

        # --------------------------------------------------
        # MAIN QUERY: Join against aggregated findings
        # --------------------------------------------------

        query = (
            db.session.query(
                AWSResourceInventory.service_name.label("service"),

                func.count(
                    func.distinct(AWSResourceInventory.id)
                ).label("total_resources"),

                func.coalesce(
                    func.sum(findings_subq.c.f_total), 0
                ).label("total_findings"),

                func.coalesce(
                    func.sum(findings_subq.c.f_high), 0
                ).label("high_count"),

                func.coalesce(
                    func.sum(findings_subq.c.f_medium), 0
                ).label("medium_count"),

                func.coalesce(
                    func.sum(findings_subq.c.f_low), 0
                ).label("low_count"),

                func.max(
                    findings_subq.c.f_max_severity_rank
                ).label("max_severity_rank"),
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

        results = query.all()

        data = []

        for r in results:

            total_resources = int(r.total_resources or 0)
            total_findings = int(r.total_findings or 0)
            high = int(r.high_count or 0)
            medium = int(r.medium_count or 0)
            low = int(r.low_count or 0)

            # ----------------------------
            # HEALTH SCORE LOGIC
            # ----------------------------

            risk_points = (high * 10) + (medium * 5) + (low * 2)

            if total_resources > 0:
                risk_per_resource = risk_points / total_resources
                health_score = max(0, 100 - (risk_per_resource * 10))
            else:
                health_score = 100

            health_score = round(health_score)

            # ----------------------------
            # RISK LEVEL LABEL
            # ----------------------------

            if health_score >= 85:
                risk_level = "LOW"
            elif health_score >= 60:
                risk_level = "MEDIUM"
            else:
                risk_level = "HIGH"

            data.append({
                "service": r.service,
                "total_resources": total_resources,
                "total_findings": total_findings,
                "high": high,
                "medium": medium,
                "low": low,
                "health_score": health_score,
                "risk_level": risk_level
            })

        return data
    
# ======================================================
# RESOURCES BY SERVICE (ENTERPRISE HARDENED)
# ======================================================
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

        # -----------------------------------------
        # FILTRO POR SEVERIDAD MÍNIMA
        # -----------------------------------------

        severity_map = {
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3
        }

        if min_severity and min_severity in severity_map:
            base_query = base_query.having(
                func.max(severity_rank) >= severity_map[min_severity]
            )

        # -----------------------------------------
        # ORDENAMIENTO
        # -----------------------------------------

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
            base_query = base_query.order_by(
                AWSResourceInventory.detected_at.asc()
            )
        else:
            base_query = base_query.order_by(
                func.max(severity_rank).desc()
            )

        # -----------------------------------------
        # PAGINACIÓN
        # -----------------------------------------

        per_page = min(max(per_page, 1), 200)

        pagination = base_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        results = pagination.items

        now = datetime.utcnow()

        data = []

        for r in results:

            aging_days = (
                (now - r.detected_at).days
                if r.detected_at else 0
            )

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
                "risk_score": risk_score
            })

        return {
            "items": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages
            }
        }
    
# ======================================================
# GLOBAL HEALTH SCORE (ENTERPRISE SAFE)
# ======================================================
    @staticmethod
    def get_global_health_score(client_id):

        query = (
            db.session.query(
                func.count(func.distinct(AWSResourceInventory.id)).label("total_resources"),

                func.sum(
                    case((AWSFinding.severity == "HIGH", 1), else_=0)
                ).label("high_count"),

                func.sum(
                    case((AWSFinding.severity == "MEDIUM", 1), else_=0)
                ).label("medium_count"),

                func.sum(
                    case((AWSFinding.severity == "LOW", 1), else_=0)
                ).label("low_count"),

                func.count(AWSFinding.id).label("total_findings")
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
        total_findings = result.total_findings or 0

        # ----------------------------
        # HEALTH SCORE LOGIC
        # ----------------------------

        risk_points = (high * 10) + (medium * 5) + (low * 2)

        if total_resources > 0:
            risk_per_resource = risk_points / total_resources
            health_score = max(0, 100 - (risk_per_resource * 10))
        else:
            health_score = 100

        health_score = round(health_score)

        # ----------------------------
        # RISK LEVEL
        # ----------------------------

        if health_score >= 85:
            risk_level = "LOW"
        elif health_score >= 60:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        return {
            "health_score": health_score,
            "risk_level": risk_level,
            "total_resources": total_resources,
            "total_findings": total_findings,
            "high": high,
            "medium": medium,
            "low": low
        }
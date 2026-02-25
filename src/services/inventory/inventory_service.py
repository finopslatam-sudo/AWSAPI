from sqlalchemy import func, case, and_
from datetime import datetime

from src.models.database import db
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding


class InventoryService:

    # ======================================================
    # SERVICES SUMMARY (ENTERPRISE SAFE)
    # ======================================================

    @staticmethod
    def get_services_summary(client_id):

        query = (
            db.session.query(
                AWSResourceInventory.service_name.label("service"),

                # Total recursos activos
                func.count(
                    func.distinct(AWSResourceInventory.id)
                ).label("total_resources"),

                # Total findings abiertos
                func.count(AWSFinding.id).label("total_findings"),

                # Severidad máxima
                func.max(
                    case(
                        (AWSFinding.severity == "LOW", 1),
                        (AWSFinding.severity == "MEDIUM", 2),
                        (AWSFinding.severity == "HIGH", 3),
                        else_=0
                    )
                ).label("max_severity_rank"),

                # Conteo por severidad
                func.sum(
                    case((AWSFinding.severity == "HIGH", 1), else_=0)
                ).label("high_count"),

                func.sum(
                    case((AWSFinding.severity == "MEDIUM", 1), else_=0)
                ).label("medium_count"),

                func.sum(
                    case((AWSFinding.severity == "LOW", 1), else_=0)
                ).label("low_count"),
            )

            # LEFT JOIN CONTROLADO
            .outerjoin(
                AWSFinding,
                and_(
                    AWSFinding.resource_id == AWSResourceInventory.resource_id,
                    AWSFinding.client_id == client_id,
                    AWSFinding.resolved == False
                )
            )

            # Filtros inventario
            .filter(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.is_active == True
            )

            .group_by(
                AWSResourceInventory.service_name
            )
        )

        results = query.all()

        severity_map = {
            1: "LOW",
            2: "MEDIUM",
            3: "HIGH"
        }

        return [
            {
                "service": r.service,
                "total_resources": r.total_resources or 0,
                "total_findings": r.total_findings or 0,
                "max_severity": severity_map.get(r.max_severity_rank),
                "high": r.high_count or 0,
                "medium": r.medium_count or 0,
                "low": r.low_count or 0,
            }
            for r in results
        ]
    

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
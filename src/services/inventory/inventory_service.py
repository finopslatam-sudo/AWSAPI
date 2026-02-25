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
# RESOURCES BY SERVICE (ENTERPRISE DETAIL)
# ======================================================

    @staticmethod
    def get_resources_by_service(client_id, service_name):

        severity_rank = case(
            (AWSFinding.severity == "LOW", 1),
            (AWSFinding.severity == "MEDIUM", 2),
            (AWSFinding.severity == "HIGH", 3),
            else_=0
        )

        query = (
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

        results = query.all()

        severity_map = {
            1: "LOW",
            2: "MEDIUM",
            3: "HIGH"
        }

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
                "max_severity": severity_map.get(r.max_severity_rank),
                "aging_days": aging_days,
                "risk_score": risk_score
            })

        return data
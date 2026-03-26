from sqlalchemy import func, case, and_
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db


class RiskService:

    # =====================================================
    # GLOBAL RISK SCORE (ENTERPRISE OPTIMIZED)
    # =====================================================
    @staticmethod
    def get_risk_score(
        client_id: int,
        aws_account_id: int | None = None
    ):

        # ---------------------------------
        # 1️⃣ Total active resources
        # ---------------------------------
        total_resources_query = db.session.query(
            func.count(AWSResourceInventory.id)
        ).filter(
            AWSResourceInventory.client_id == client_id,
            AWSResourceInventory.is_active.is_(True)
        )

        if aws_account_id is not None:
            total_resources_query = total_resources_query.filter(
                AWSResourceInventory.aws_account_id == aws_account_id
            )

        total_resources = total_resources_query.scalar() or 0

        if total_resources == 0:
            return {
                "risk_score": 100.0,
                "risk_level": "LOW",
                "risk_points": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }

        # ---------------------------------
        # 2️⃣ Aggregate severities in single query
        # ---------------------------------
        results_query = (
            db.session.query(
                func.sum(case((AWSFinding.severity == "HIGH", 1), else_=0)).label("high"),
                func.sum(case((AWSFinding.severity == "MEDIUM", 1), else_=0)).label("medium"),
                func.sum(case((AWSFinding.severity == "LOW", 1), else_=0)).label("low")
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
                AWSFinding.resolved.is_(False),
                AWSResourceInventory.is_active.is_(True)
            )
        )

        if aws_account_id is not None:
            results_query = results_query.filter(
                AWSFinding.aws_account_id == aws_account_id,
                AWSResourceInventory.aws_account_id == aws_account_id
            )

        results = results_query.first()

        high = results.high or 0
        medium = results.medium or 0
        low = results.low or 0

        # ---------------------------------
        # 3️⃣ Risk calculation
        # ---------------------------------
        risk_points = (high * 5) + (medium * 3) + (low * 1)
        max_risk = total_resources * 5

        risk_score = 100 - ((risk_points / max_risk) * 100)
        risk_score = max(min(risk_score, 100), 0)  # clamp 0–100
        risk_score = round(risk_score, 2)

        risk_level = RiskService._calculate_risk_level(risk_score)

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_points": risk_points,
            "high": high,
            "medium": medium,
            "low": low
        }

    # =====================================================
    # RISK BREAKDOWN BY SERVICE (NO N+1)
    # =====================================================
    @staticmethod
    def get_risk_breakdown_by_service(
        client_id: int,
        aws_account_id: int | None = None
    ):

        results_query = (
            db.session.query(
                AWSResourceInventory.service_name,
                func.count(AWSResourceInventory.id).label("total_resources"),
                func.sum(case((AWSFinding.severity == "HIGH", 1), else_=0)).label("high"),
                func.sum(case((AWSFinding.severity == "MEDIUM", 1), else_=0)).label("medium"),
                func.sum(case((AWSFinding.severity == "LOW", 1), else_=0)).label("low")
            )
            .outerjoin(
                AWSFinding,
                and_(
                    AWSFinding.resource_id == AWSResourceInventory.resource_id,
                    AWSFinding.client_id == AWSResourceInventory.client_id,
                    AWSFinding.resolved.is_(False)
                )
            )
            .filter(
                AWSResourceInventory.client_id == client_id,
                AWSResourceInventory.is_active.is_(True)
            )
        )

        if aws_account_id is not None:
            results_query = results_query.filter(
                AWSResourceInventory.aws_account_id == aws_account_id
            )

        results = (
            results_query
            .group_by(AWSResourceInventory.service_name)
            .all()
        )

        breakdown = {}

        for row in results:

            high = row.high or 0
            medium = row.medium or 0
            low = row.low or 0

            risk_points = (high * 5) + (medium * 3) + (low * 1)
            max_risk = row.total_resources * 5

            risk_score = (
                100 - ((risk_points / max_risk) * 100)
                if max_risk else 100
            )

            risk_score = max(min(risk_score, 100), 0)
            risk_score = round(risk_score, 2)

            breakdown[row.service_name] = {
                "risk_score": risk_score,
                "risk_level": RiskService._calculate_risk_level(risk_score),
                "high": high,
                "medium": medium,
                "low": low,
                "total_resources": row.total_resources
            }

        return breakdown

    # =====================================================
    # PRIORITIZATION ENGINE
    # =====================================================
    @staticmethod
    def get_priority_services(
        client_id: int,
        aws_account_id: int | None = None,
        breakdown: dict | None = None,  # pre-computed para evitar query duplicada
    ):

        if breakdown is None:
            breakdown = RiskService.get_risk_breakdown_by_service(
                client_id,
                aws_account_id
            )

        services_list = [
            {
                "service": service,
                "risk_score": data["risk_score"],
                "risk_level": data["risk_level"],
                "high": data["high"],
                "medium": data["medium"],
                "low": data["low"]
            }
            for service, data in breakdown.items()
        ]

        services_list.sort(
            key=lambda x: (
                x["risk_score"],   # menor score = peor
                -x["high"],
                -x["medium"]
            )
        )

        return services_list

    # =====================================================
    # INTERNAL RISK LEVEL CALCULATOR
    # =====================================================
    @staticmethod
    def _calculate_risk_level(risk_score: float):

        if risk_score >= 80:
            return "LOW"
        elif risk_score >= 60:
            return "MODERATE"
        elif risk_score >= 40:
            return "HIGH"
        else:
            return "CRITICAL"

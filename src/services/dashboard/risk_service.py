from sqlalchemy import func
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db


class RiskService:

   # =====================================================
    # RISK SCORE GLOBAL
    # =====================================================
    @staticmethod
    def get_risk_score(client_id: int):

        total_resources = db.session.query(
            AWSResourceInventory.id
        ).filter_by(
            client_id=client_id,
            is_active=True
        ).count()

        # Si no hay recursos → no hay riesgo
        if total_resources == 0:
            return {
                "risk_score": 100.0,
                "risk_level": "LOW",
                "risk_points": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }

        # ---------------- ACTIVE FINDINGS ----------------
        high = AWSFinding.query.filter_by(
            client_id=client_id,
            severity="HIGH",
            resolved=False
        ).count()

        medium = AWSFinding.query.filter_by(
            client_id=client_id,
            severity="MEDIUM",
            resolved=False
        ).count()

        low = AWSFinding.query.filter_by(
            client_id=client_id,
            severity="LOW",
            resolved=False
        ).count()

        # ---------------- RISK CALCULATION ----------------
        risk_points = (high * 5) + (medium * 3) + (low * 1)

        max_risk = total_resources * 5

        risk_score = 100 - ((risk_points / max_risk) * 100) if max_risk else 100
        risk_score = round(risk_score, 2)

        # ---------------- RISK LEVEL ----------------
        if risk_score >= 80:
            risk_level = "LOW"
        elif risk_score >= 60:
            risk_level = "MODERATE"
        elif risk_score >= 40:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_points": risk_points,
            "high": high,
            "medium": medium,
            "low": low
        }
    
    # =====================================================
    # RISK BREAKDOWN BY SERVICE
    # =====================================================
    @staticmethod
    def get_risk_breakdown_by_service(client_id: int):

        services = db.session.query(
            AWSResourceInventory.resource_type,
            func.count(AWSResourceInventory.id)
        ).filter_by(
            client_id=client_id,
            is_active=True
        ).group_by(
            AWSResourceInventory.resource_type
        ).all()

        breakdown = {}

        for service, total_resources in services:

            if total_resources == 0:
                continue

            high = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_type=service,
                severity="HIGH",
                resolved=False
            ).count()

            medium = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_type=service,
                severity="MEDIUM",
                resolved=False
            ).count()

            low = AWSFinding.query.filter_by(
                client_id=client_id,
                resource_type=service,
                severity="LOW",
                resolved=False
            ).count()

            risk_points = (high * 5) + (medium * 3) + (low * 1)
            max_risk = total_resources * 5

            risk_score = 100 - ((risk_points / max_risk) * 100) if max_risk else 100
            risk_score = round(risk_score, 2)

            if risk_score >= 80:
                risk_level = "LOW"
            elif risk_score >= 60:
                risk_level = "MODERATE"
            elif risk_score >= 40:
                risk_level = "HIGH"
            else:
                risk_level = "CRITICAL"

            breakdown[service] = {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "high": high,
                "medium": medium,
                "low": low,
                "total_resources": total_resources
            }

        return breakdown
    
    # =====================================================
    # SERVICE PRIORITIZATION ENGINE
    # =====================================================
    @staticmethod
    def get_priority_services(client_id: int):

        breakdown = RiskService.get_risk_breakdown_by_service(client_id)

        services_list = []

        for service, data in breakdown.items():
            services_list.append({
                "service": service,
                "risk_score": data["risk_score"],
                "risk_level": data["risk_level"],
                "high": data["high"],
                "medium": data["medium"],
                "low": data["low"]
            })

        # Ordenamiento inteligente:
        # 1️⃣ menor risk_score primero
        # 2️⃣ más HIGH findings
        # 3️⃣ más MEDIUM findings
        services_list.sort(
            key=lambda x: (
                x["risk_score"],
                -x["high"],
                -x["medium"]
            )
        )

        return services_list
    
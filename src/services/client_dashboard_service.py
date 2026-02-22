from sqlalchemy import func
from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db
from src.aws.cost_explorer_service import CostExplorerService


class ClientDashboardService:

    # =====================================================
    # SUMMARY GENERAL
    # =====================================================
    @staticmethod
    def get_summary(client_id: int):

        # ---------------- FINDINGS STATS ----------------
        base_query = AWSFinding.query.filter_by(client_id=client_id)

        total = base_query.count()
        active = base_query.filter_by(resolved=False).count()
        resolved = base_query.filter_by(resolved=True).count()

        high = base_query.filter_by(severity="HIGH", resolved=False).count()
        medium = base_query.filter_by(severity="MEDIUM", resolved=False).count()
        low = base_query.filter_by(severity="LOW", resolved=False).count()

        savings = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        # ---------------- AWS ACCOUNTS ----------------
        accounts_count = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).count()

        # ---------------- LAST SYNC ----------------
        last_sync = db.session.query(
            func.max(AWSAccount.last_sync)
        ).filter_by(
            client_id=client_id,
            is_active=True
        ).scalar()

        # ---------------- RESOURCES AFFECTED ----------------
        resources_affected = db.session.query(
            func.count(func.distinct(AWSFinding.resource_id))
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        # ---------------- GOVERNANCE & RISK ----------------
        governance = ClientDashboardService.get_governance_score(client_id)
        risk = ClientDashboardService.get_risk_score(client_id)
        risk_by_service = ClientDashboardService.get_risk_breakdown_by_service(client_id)
        priority_services = ClientDashboardService.get_priority_services(client_id)

        return {
            "findings": {
                "total": total,
                "active": active,
                "resolved": resolved,
                "high": high,
                "medium": medium,
                "low": low,
                "estimated_monthly_savings": float(savings)
            },
            "accounts": accounts_count,
            "last_sync": last_sync.isoformat() if last_sync else None,
            "resources_affected": resources_affected,
            "governance": governance,
            "risk": risk,
            "risk_by_service": risk_by_service,
            "priority_services": priority_services
        }

    # =====================================================
    # COST DATA
    # =====================================================
    @staticmethod
    def get_cost_data(client_id: int):

        aws_account = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).first()

        if not aws_account:
            return {
                "monthly_cost": [],
                "service_breakdown": [],
                "current_month_cost": 0,
                "potential_savings": 0,
                "savings_percentage": 0
            }

        ce = CostExplorerService(aws_account)

        monthly_cost_raw = ce.get_last_6_months_cost()

        monthly_cost = []
        for item in monthly_cost_raw:
            amount = float(item["amount"])
            if abs(amount) < 0.01:
                amount = 0.0

            monthly_cost.append({
                "month": item["month"],
                "amount": amount
            })

        service_breakdown = ce.get_service_breakdown_current_month()

        raw_current_month_cost = monthly_cost[-1]["amount"] if monthly_cost else 0
        current_month_cost = 0 if abs(raw_current_month_cost) < 0.01 else float(raw_current_month_cost)

        savings = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        if current_month_cost <= 0:
            savings_percentage = 0
        else:
            savings_percentage = round((float(savings) / current_month_cost) * 100, 2)

        return {
            "monthly_cost": monthly_cost,
            "service_breakdown": service_breakdown,
            "current_month_cost": float(current_month_cost),
            "potential_savings": float(savings),
            "savings_percentage": round(savings_percentage, 2)
        }

    # =====================================================
    # INVENTORY SUMMARY
    # =====================================================
    @staticmethod
    def get_inventory_summary(client_id: int):

        findings = db.session.query(
            AWSFinding.resource_type,
            func.count(AWSFinding.id)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).group_by(
            AWSFinding.resource_type
        ).all()

        services = [
            {
                "service": resource_type,
                "active_findings": count
            }
            for resource_type, count in findings
        ]

        return services

    # =====================================================
    # GOVERNANCE SCORE
    # =====================================================
    @staticmethod
    def get_governance_score(client_id: int):

        total_resources = db.session.query(
            AWSResourceInventory.id
        ).filter_by(
            client_id=client_id,
            is_active=True
        ).count()

        if total_resources == 0:
            return {
                "total_resources": 0,
                "non_compliant_resources": 0,
                "compliant_resources": 0,
                "compliance_percentage": 100.0
            }

        non_compliant_resources = db.session.query(
            func.count(func.distinct(AWSFinding.resource_id))
        ).filter(
            AWSFinding.client_id == client_id,
            AWSFinding.resolved == False,
            AWSFinding.finding_type.like("MISSING_TAG%")
        ).scalar() or 0

        compliant_resources = total_resources - non_compliant_resources

        compliance_percentage = round(
            (compliant_resources / total_resources) * 100,
            2
        )

        return {
            "total_resources": total_resources,
            "non_compliant_resources": non_compliant_resources,
            "compliant_resources": compliant_resources,
            "compliance_percentage": compliance_percentage
        }

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

        breakdown = ClientDashboardService.get_risk_breakdown_by_service(client_id)

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
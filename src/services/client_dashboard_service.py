from sqlalchemy import func
from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount
from src.models.database import db
from src.aws.cost_explorer_service import CostExplorerService

# 👇 IMPORTANTE: usar la nueva fachada
from src.services.dashboard.facade import ClientDashboardFacade


class ClientDashboardService:

    # =====================================================
    # SUMMARY GENERAL (Delegado al Facade)
    # =====================================================
    @staticmethod
    def get_summary(client_id: int):
        return ClientDashboardFacade.get_summary(client_id)

    # =====================================================
    # COST DATA (se mantiene aquí por ahora)
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
        current_month_cost = (
            0 if abs(raw_current_month_cost) < 0.01
            else float(raw_current_month_cost)
        )

        savings = db.session.query(
            func.sum(AWSFinding.estimated_monthly_savings)
        ).filter_by(
            client_id=client_id,
            resolved=False
        ).scalar() or 0

        if current_month_cost <= 0:
            savings_percentage = 0
        else:
            savings_percentage = round(
                (float(savings) / current_month_cost) * 100,
                2
            )

        return {
            "monthly_cost": monthly_cost,
            "service_breakdown": service_breakdown,
            "current_month_cost": float(current_month_cost),
            "potential_savings": float(savings),
            "savings_percentage": round(savings_percentage, 2)
        }

    # =====================================================
    # INVENTORY SUMMARY (se mantiene aquí por ahora)
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
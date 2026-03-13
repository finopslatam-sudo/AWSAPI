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
    # COST DATA (MULTI ACCOUNT SAFE)
    # =====================================================
    @staticmethod
    def get_cost_data(client_id: int):

        aws_accounts = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        ).all()

        if not aws_accounts:
            return {
                "monthly_cost": [],
                "service_breakdown": [],
                "current_month_cost": 0,
                "potential_savings": 0,
                "savings_percentage": 0
            }

        # =====================================================
        # ACUMULADORES MULTI-CUENTA
        # =====================================================

        monthly_cost_map = {}
        service_breakdown_map = {}

        # =====================================================
        # ITERAR TODAS LAS CUENTAS AWS DEL CLIENTE
        # =====================================================

        for aws_account in aws_accounts:

            try:

                ce = CostExplorerService(aws_account)

                # ===============================
                # COSTO MENSUAL (6 MESES)
                # ===============================

                monthly_cost_raw = ce.get_last_6_months_cost()

                for item in monthly_cost_raw:

                    month = item["month"]
                    amount = float(item["amount"])

                    if abs(amount) < 0.01:
                        amount = 0.0

                    monthly_cost_map[month] = (
                        monthly_cost_map.get(month, 0) + amount
                    )

                # ===============================
                # COSTO POR SERVICIO
                # ===============================

                services = ce.get_service_breakdown_current_month()

                for svc in services:

                    service = svc["service"]
                    amount = float(svc["amount"])

                    service_breakdown_map[service] = (
                        service_breakdown_map.get(service, 0) + amount
                    )

            except Exception:
                # si una cuenta falla no rompe el dashboard
                continue

        # =====================================================
        # NORMALIZAR COSTO MENSUAL
        # =====================================================

        monthly_cost = [
            {
                "month": month,
                "amount": float(amount)
            }
            for month, amount in sorted(monthly_cost_map.items())
        ]

        raw_current_month_cost = monthly_cost[-1]["amount"] if monthly_cost else 0

        current_month_cost = (
            0 if abs(raw_current_month_cost) < 0.01
            else float(raw_current_month_cost)
        )

        # =====================================================
        # NORMALIZAR BREAKDOWN POR SERVICIO
        # =====================================================

        service_breakdown = [
            {
                "service": service,
                "amount": float(amount)
            }
            for service, amount in service_breakdown_map.items()
        ]

        # =====================================================
        # POTENTIAL SAVINGS
        # =====================================================

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
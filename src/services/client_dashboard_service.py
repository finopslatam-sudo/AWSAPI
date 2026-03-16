from datetime import date

from sqlalchemy import func

from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount
from src.models.database import db
from src.aws.cost_explorer_service import CostExplorerService


class ClientDashboardService:

    @staticmethod
    def _get_active_savings_subquery(
        client_id: int,
        aws_account_id: int | None = None
    ):

        savings_query = db.session.query(
            AWSFinding.aws_account_id.label("aws_account_id"),
            AWSFinding.resource_id.label("resource_id"),
            AWSFinding.finding_type.label("finding_type"),
            func.max(
                func.coalesce(
                    AWSFinding.estimated_monthly_savings,
                    0
                )
            ).label("estimated_monthly_savings")
        ).filter(
            AWSFinding.client_id == client_id,
            AWSFinding.resolved.is_(False)
        )

        if aws_account_id is not None:
            savings_query = savings_query.filter(
                AWSFinding.aws_account_id == aws_account_id
            )

        return savings_query.group_by(
            AWSFinding.aws_account_id,
            AWSFinding.resource_id,
            AWSFinding.finding_type
        ).subquery()

    # =====================================================
    # COST DATA (MULTI ACCOUNT SAFE)
    # =====================================================
    @staticmethod
    def get_cost_data(client_id: int, aws_account_id: int | None = None):

        query = AWSAccount.query.filter_by(
            client_id=client_id,
            is_active=True
        )

        # =====================================================
        # ACCOUNT FILTER
        # =====================================================

        if aws_account_id is not None:
            query = query.filter(
                AWSAccount.id == aws_account_id
            )

        aws_accounts = query.all()

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
        current_month_key = date.today().strftime("%Y-%m")

        # Compare monthly savings against a full-month spend baseline.
        # If the latest point is the current partial month, we fallback
        # to the last closed month when available.
        current_month_cost = float(raw_current_month_cost)

        if monthly_cost:
            latest_month = monthly_cost[-1]["month"]

            if latest_month == current_month_key and len(monthly_cost) > 1:
                current_month_cost = float(monthly_cost[-2]["amount"])

        current_month_cost = (
            0 if abs(current_month_cost) < 0.01
            else float(current_month_cost)
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

        active_savings = ClientDashboardService._get_active_savings_subquery(
            client_id,
            aws_account_id
        )

        savings = db.session.query(
            func.sum(active_savings.c.estimated_monthly_savings)
        ).scalar() or 0

        if current_month_cost <= 0:
            savings_percentage = 0
        else:
            raw_savings_percentage = (
                float(savings) / current_month_cost
            ) * 100
            savings_percentage = round(
                min(raw_savings_percentage, 100.0),
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
    def get_inventory_summary(
        client_id: int,
        aws_account_id: int | None = None
    ):

        findings_query = db.session.query(
            AWSFinding.resource_type,
            func.count(AWSFinding.id)
        ).filter_by(
            client_id=client_id,
            resolved=False
        )

        if aws_account_id is not None:
            findings_query = findings_query.filter(
                AWSFinding.aws_account_id == aws_account_id
            )

        findings = findings_query.group_by(
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

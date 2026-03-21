from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

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
        previous_year_total = 0.0
        current_year_ytd_total = 0.0

        # Date reference points
        today = date.today()
        current_month_key = today.strftime("%Y-%m")
        curr_year = today.year
        prev_year = curr_year - 1
        prev_month_start = today.replace(day=1) - relativedelta(months=1)
        prev_month_end = today.replace(day=1) - timedelta(days=1)

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

                # ===============================
                # COSTOS ANUALES
                # ===============================

                annual = ce.get_annual_costs()
                previous_year_total += annual["previous_year_cost"]
                current_year_ytd_total += annual["current_year_ytd"]

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

        # Gasto parcial del mes en curso
        current_month_partial = 0.0
        if monthly_cost and monthly_cost[-1]["month"] == current_month_key:
            current_month_partial = float(monthly_cost[-1]["amount"])

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

        savings_f = float(savings)

        if current_month_cost <= 0:
            savings_percentage = 0.0
        else:
            savings_percentage = round(
                min((savings_f / current_month_cost) * 100, 100.0), 2
            )

        # =====================================================
        # CALCULOS ANUALES
        # =====================================================

        annual_estimated_savings = round(savings_f * 12, 2)

        if previous_year_total > 0:
            annual_savings_percentage = round(
                min((annual_estimated_savings / previous_year_total) * 100, 100.0), 2
            )
        else:
            annual_savings_percentage = 0.0

        if current_month_partial > 0:
            current_month_savings_percentage = round(
                min((savings_f / current_month_partial) * 100, 100.0), 2
            )
        else:
            current_month_savings_percentage = 0.0

        return {
            # Campos originales (backward compat)
            "monthly_cost": monthly_cost,
            "service_breakdown": service_breakdown,
            "current_month_cost": current_month_cost,
            "potential_savings": savings_f,
            "savings_percentage": savings_percentage,
            # Nuevos campos
            "previous_month_cost": current_month_cost,
            "current_month_partial": current_month_partial,
            "previous_year_cost": round(previous_year_total, 2),
            "current_year_ytd": round(current_year_ytd_total, 2),
            "annual_estimated_savings": annual_estimated_savings,
            "monthly_savings_percentage": savings_percentage,
            "annual_savings_percentage": annual_savings_percentage,
            "current_month_savings_percentage": current_month_savings_percentage,
            "date_labels": {
                "previous_month_start": prev_month_start.isoformat(),
                "previous_month_end": prev_month_end.isoformat(),
                "current_month_start": today.replace(day=1).isoformat(),
                "current_month_end": today.isoformat(),
                "previous_year_start": f"{prev_year}-01-01",
                "previous_year_end": f"{prev_year}-12-31",
                "current_year_start": f"{curr_year}-01-01",
                "current_year_end": today.isoformat(),
            }
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

    @staticmethod
    def get_savings_breakdown(
        client_id: int,
        aws_account_id: int | None = None
    ):

        findings_query = db.session.query(
            AWSFinding.id,
            AWSFinding.aws_account_id,
            AWSAccount.account_name,
            AWSFinding.resource_id,
            AWSFinding.resource_type,
            AWSFinding.aws_service,
            AWSFinding.finding_type,
            AWSFinding.severity,
            func.coalesce(
                AWSFinding.estimated_monthly_savings,
                0
            ).label("estimated_monthly_savings"),
            AWSFinding.detected_at
        ).join(
            AWSAccount,
            AWSFinding.aws_account_id == AWSAccount.id
        ).filter(
            AWSFinding.client_id == client_id,
            AWSFinding.resolved.is_(False)
        )

        if aws_account_id is not None:
            findings_query = findings_query.filter(
                AWSFinding.aws_account_id == aws_account_id
            )

        findings = findings_query.order_by(
            func.coalesce(
                AWSFinding.estimated_monthly_savings,
                0
            ).desc(),
            AWSFinding.detected_at.desc()
        ).all()

        dedup_subquery = ClientDashboardService._get_active_savings_subquery(
            client_id,
            aws_account_id
        )

        dedup_total = db.session.query(
            func.sum(dedup_subquery.c.estimated_monthly_savings)
        ).scalar() or 0

        raw_total = sum(
            float(item.estimated_monthly_savings or 0)
            for item in findings
        )

        grouped = {}

        for item in findings:
            account_key = str(item.aws_account_id)

            if account_key not in grouped:
                grouped[account_key] = {
                    "aws_account_id": item.aws_account_id,
                    "account_name": item.account_name,
                    "raw_total_savings": 0.0,
                    "findings_count": 0,
                    "items": []
                }

            savings = float(item.estimated_monthly_savings or 0)

            grouped[account_key]["raw_total_savings"] += savings
            grouped[account_key]["findings_count"] += 1
            grouped[account_key]["items"].append({
                "finding_id": item.id,
                "resource_id": item.resource_id,
                "resource_type": item.resource_type,
                "aws_service": item.aws_service,
                "finding_type": item.finding_type,
                "severity": item.severity,
                "estimated_monthly_savings": savings,
                "detected_at": (
                    item.detected_at.isoformat()
                    if item.detected_at else None
                )
            })

        return {
            "aws_account_id": aws_account_id,
            "raw_total_savings": round(float(raw_total), 2),
            "deduplicated_total_savings": round(float(dedup_total), 2),
            "accounts": list(grouped.values())
        }

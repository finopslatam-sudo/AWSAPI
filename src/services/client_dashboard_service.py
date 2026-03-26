from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from sqlalchemy import func

from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount
from src.models.database import db
from src.services.cost_explorer_cache_service import CostExplorerCacheService as CostExplorerService

# Query helpers live in a dedicated module to keep this file < 300 lines.
from src.services.client_dashboard_queries import (
    get_active_savings_subquery,
    query_savings_breakdown_findings,
    group_findings_by_account,
    accumulate_cost_data,
)


def _r2(value: float) -> float:
    """
    Round to 2 decimal places using integer arithmetic.
    Avoids the Pyright overload-resolution bug with round(x, ndigits).
    """
    return float(int(value * 100 + 0.5) / 100)


class ClientDashboardService:

    @staticmethod
    def _get_active_savings_subquery(
        client_id: int,
        aws_account_id: int | None = None
    ):
        return get_active_savings_subquery(client_id, aws_account_id)

    # =====================================================
    # COST DATA (MULTI ACCOUNT SAFE)
    # =====================================================
    @staticmethod
    def get_cost_data(client_id: int, aws_account_id: int | None = None):

        query = AWSAccount.query.filter_by(client_id=client_id, is_active=True)

        if aws_account_id is not None:
            query = query.filter(AWSAccount.id == aws_account_id)

        aws_accounts = query.all()

        if not aws_accounts:
            return {
                "monthly_cost": [],
                "service_breakdown": [],
                "current_month_cost": 0,
                "potential_savings": 0,
                "savings_percentage": 0
            }

        # Date reference points
        today = date.today()
        current_month_key = today.strftime("%Y-%m")
        curr_year = today.year
        prev_year = curr_year - 1
        prev_month_start = today.replace(day=1) - relativedelta(months=1)
        prev_month_end = today.replace(day=1) - timedelta(days=1)

        # Accumulate data across all accounts
        (
            monthly_cost_map,
            service_breakdown_map,
            previous_year_total,
            current_year_ytd_total,
        ) = accumulate_cost_data(aws_accounts, CostExplorerService)

        # ---- Normalise monthly cost list ----
        monthly_cost = [
            {"month": month, "amount": float(amount)}
            for month, amount in sorted(monthly_cost_map.items())
        ]

        raw_current_month_cost = monthly_cost[-1]["amount"] if monthly_cost else 0
        current_month_cost = float(raw_current_month_cost)

        if monthly_cost:
            latest_month = monthly_cost[-1]["month"]
            if latest_month == current_month_key and len(monthly_cost) > 1:
                current_month_cost = float(monthly_cost[-2]["amount"])

        current_month_cost = (
            0.0 if abs(current_month_cost) < 0.01 else float(current_month_cost)
        )

        current_month_partial = 0.0
        if monthly_cost and monthly_cost[-1]["month"] == current_month_key:
            current_month_partial = float(monthly_cost[-1]["amount"])

        # ---- Normalise service breakdown ----
        service_breakdown = [
            {"service": service, "amount": float(amount)}
            for service, amount in service_breakdown_map.items()
        ]

        # ---- Potential savings ----
        active_savings = get_active_savings_subquery(client_id, aws_account_id)

        savings = db.session.query(
            func.sum(active_savings.c.estimated_monthly_savings)
        ).scalar() or 0

        savings_f = float(savings)

        savings_percentage = (
            0.0 if current_month_cost <= 0
            else _r2(float(min((savings_f / current_month_cost) * 100, 100.0)))
        )

        # ---- Annual calculations ----
        annual_estimated_savings = _r2(savings_f * 12)

        annual_savings_percentage = (
            _r2(float(min((annual_estimated_savings / previous_year_total) * 100, 100.0)))
            if previous_year_total > 0 else 0.0
        )

        current_month_savings_percentage = (
            _r2(float(min((savings_f / current_month_partial) * 100, 100.0)))
            if current_month_partial > 0 else 0.0
        )

        return {
            # Original fields (backward compat)
            "monthly_cost": monthly_cost,
            "service_breakdown": service_breakdown,
            "current_month_cost": current_month_cost,
            "potential_savings": savings_f,
            "savings_percentage": savings_percentage,
            # New fields
            "previous_month_cost": current_month_cost,
            "current_month_partial": current_month_partial,
            "previous_year_cost": _r2(float(previous_year_total)),
            "current_year_ytd": _r2(float(current_year_ytd_total)),
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
    # INVENTORY SUMMARY
    # =====================================================
    @staticmethod
    def get_inventory_summary(
        client_id: int,
        aws_account_id: int | None = None
    ):

        findings_query = db.session.query(
            AWSFinding.resource_type,
            func.count(AWSFinding.id)
        ).filter_by(client_id=client_id, resolved=False)

        if aws_account_id is not None:
            findings_query = findings_query.filter(
                AWSFinding.aws_account_id == aws_account_id
            )

        findings = findings_query.group_by(AWSFinding.resource_type).all()

        return [
            {"service": resource_type, "active_findings": count}
            for resource_type, count in findings
        ]

    # =====================================================
    # SAVINGS BREAKDOWN
    # =====================================================
    @staticmethod
    def get_savings_breakdown(
        client_id: int,
        aws_account_id: int | None = None
    ):

        findings = query_savings_breakdown_findings(client_id, aws_account_id)

        dedup_subquery = get_active_savings_subquery(client_id, aws_account_id)

        dedup_total = db.session.query(
            func.sum(dedup_subquery.c.estimated_monthly_savings)
        ).scalar() or 0

        grouped, raw_total = group_findings_by_account(findings)

        return {
            "aws_account_id": aws_account_id,
            "raw_total_savings": _r2(float(raw_total)),
            "deduplicated_total_savings": _r2(float(dedup_total)),
            "accounts": list(grouped.values())
        }

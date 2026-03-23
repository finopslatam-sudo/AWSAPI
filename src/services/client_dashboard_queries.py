"""
client_dashboard_queries.py
---------------------------
Reusable SQLAlchemy query helpers for ClientDashboardService.

Extracted from client_dashboard_service.py to keep that module under 300 lines.
All helpers are pure functions; behaviour is identical to the original inline code.
"""

from sqlalchemy import func

from src.models.database import db
from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount


# -----------------------------------------------------------------------
# ACTIVE SAVINGS SUBQUERY
# -----------------------------------------------------------------------

def get_active_savings_subquery(
    client_id: int,
    aws_account_id: int | None = None
):
    """
    Return a subquery that deduplicates savings per
    (aws_account_id, resource_id, finding_type) combination,
    scoped to unresolved findings for the given client.
    """

    savings_query = db.session.query(
        AWSFinding.aws_account_id.label("aws_account_id"),
        AWSFinding.resource_id.label("resource_id"),
        AWSFinding.finding_type.label("finding_type"),
        func.max(
            func.coalesce(AWSFinding.estimated_monthly_savings, 0)
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


# -----------------------------------------------------------------------
# SAVINGS BREAKDOWN QUERY
# -----------------------------------------------------------------------

def query_savings_breakdown_findings(
    client_id: int,
    aws_account_id: int | None = None
):
    """
    Return all unresolved findings with savings info joined to AWSAccount,
    ordered by estimated savings descending then detected_at descending.
    """

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

    return findings_query.order_by(
        func.coalesce(AWSFinding.estimated_monthly_savings, 0).desc(),
        AWSFinding.detected_at.desc()
    ).all()


# -----------------------------------------------------------------------
# SAVINGS BREAKDOWN GROUPING
# -----------------------------------------------------------------------

def group_findings_by_account(findings):
    """
    Given a flat list of finding rows (from query_savings_breakdown_findings),
    group them into a dict keyed by aws_account_id string.
    Returns (grouped_dict, raw_total).
    """

    grouped = {}
    raw_total = 0.0

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
        raw_total += savings

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

    return grouped, raw_total


# -----------------------------------------------------------------------
# COST DATA: monthly + service accumulation over multiple accounts
# -----------------------------------------------------------------------

def accumulate_cost_data(aws_accounts, CostExplorerService):
    """
    Iterate over a list of AWSAccount objects, call CostExplorerService for
    each, and return accumulated maps plus annual totals.

    Returns a tuple:
        (monthly_cost_map, service_breakdown_map,
         previous_year_total, current_year_ytd_total)
    """
    import logging

    monthly_cost_map = {}
    service_breakdown_map = {}
    previous_year_total = 0.0
    current_year_ytd_total = 0.0

    for aws_account in aws_accounts:
        try:
            ce = CostExplorerService(aws_account)

            for item in ce.get_last_6_months_cost():
                month = item["month"]
                amount = float(item["amount"])
                if abs(amount) < 0.01:
                    amount = 0.0
                monthly_cost_map[month] = monthly_cost_map.get(month, 0) + amount

            for svc in ce.get_service_breakdown_current_month():
                service = svc["service"]
                amount = float(svc["amount"])
                service_breakdown_map[service] = (
                    service_breakdown_map.get(service, 0) + amount
                )

        except Exception:
            continue

        try:
            annual = ce.get_annual_costs()
            previous_year_total += annual["previous_year_cost"]
            current_year_ytd_total += annual["current_year_ytd"]
        except Exception as e:
            logging.getLogger(__name__).warning(
                f"[annual_costs] account={aws_account.id} error={e}"
            )

    return (
        monthly_cost_map,
        service_breakdown_map,
        previous_year_total,
        current_year_ytd_total,
    )

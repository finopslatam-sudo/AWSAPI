"""
client_findings_filters.py
--------------------------
Query-building helpers shared by ClientFindingsService methods.

Extracted from client_findings_service.py to keep that module under 300 lines.
All helpers are pure functions that receive a SQLAlchemy query object and return
the filtered query, so behaviour is identical to the original inline code.
"""

from sqlalchemy import or_

from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory


# -----------------------------------------------------------------------
# COMMON FILTER HELPERS
# -----------------------------------------------------------------------

def apply_account_filter(query, aws_account_id):
    """Filter by a specific AWS account when provided."""
    if aws_account_id is not None:
        query = query.filter(AWSFinding.aws_account_id == aws_account_id)
    return query


def apply_status_filter(query, status):
    """Filter by resolved / active status string."""
    if status == "active":
        query = query.filter(AWSFinding.resolved.is_(False))
    elif status == "resolved":
        query = query.filter(AWSFinding.resolved.is_(True))
    return query


def apply_severity_filter(query, severity):
    if severity:
        query = query.filter(AWSFinding.severity == severity)
    return query


def apply_finding_type_filter(query, finding_type):
    if finding_type:
        query = query.filter(AWSFinding.finding_type == finding_type)
    return query


def apply_service_filter(query, service):
    if service:
        query = query.filter(AWSFinding.aws_service.ilike(service))
    return query


def apply_region_filter(query, region):
    if region:
        query = query.filter(AWSFinding.region.ilike(f"{region}%"))
    return query


def apply_search_filter(query, search):
    if search:
        query = query.filter(
            or_(
                AWSFinding.resource_id.ilike(f"%{search}%"),
                AWSFinding.message.ilike(f"%{search}%")
            )
        )
    return query


# -----------------------------------------------------------------------
# COMPOSITE: apply all standard optional filters at once
# -----------------------------------------------------------------------

def apply_common_filters(
    query,
    aws_account_id=None,
    status=None,
    severity=None,
    finding_type=None,
    service=None,
    search=None,
    region=None
):
    """
    Apply every optional filter in the canonical order used by both
    list_findings and get_stats.  Returns the filtered query.
    """
    query = apply_account_filter(query, aws_account_id)
    query = apply_status_filter(query, status)
    query = apply_severity_filter(query, severity)
    query = apply_finding_type_filter(query, finding_type)
    query = apply_service_filter(query, service)
    query = apply_search_filter(query, search)
    query = apply_region_filter(query, region)
    return query


# -----------------------------------------------------------------------
# SAVINGS SUBQUERY BUILDER (used by get_stats)
# -----------------------------------------------------------------------

def build_savings_subquery(
    db,
    client_id,
    aws_account_id=None,
    status=None,
    severity=None,
    finding_type=None,
    service=None,
    search=None,
    region=None
):
    """
    Build the deduplicated active-savings subquery used in get_stats.
    Returns a SQLAlchemy subquery object.
    """
    from sqlalchemy import func
    from src.models.aws_resource_inventory import AWSResourceInventory
    from sqlalchemy import and_

    savings_query = db.session.query(
        AWSFinding.aws_account_id.label("aws_account_id"),
        AWSFinding.resource_id.label("resource_id"),
        AWSFinding.finding_type.label("finding_type"),
        func.max(
            func.coalesce(AWSFinding.estimated_monthly_savings, 0)
        ).label("estimated_monthly_savings")
    ).join(
        AWSResourceInventory,
        and_(
            AWSFinding.resource_id == AWSResourceInventory.resource_id,
            AWSFinding.client_id == AWSResourceInventory.client_id
        )
    ).filter(
        AWSFinding.client_id == client_id,
        AWSResourceInventory.is_active.is_(True)
    )

    savings_query = apply_common_filters(
        savings_query,
        aws_account_id=aws_account_id,
        status=status,
        severity=severity,
        finding_type=finding_type,
        service=service,
        search=search,
        region=region
    )

    return savings_query.group_by(
        AWSFinding.aws_account_id,
        AWSFinding.resource_id,
        AWSFinding.finding_type
    ).subquery()

"""
EXECUTIVE PDF REPORT
====================
Thin orchestrator — collects data, builds the document,
delegates all visual construction to sub-modules.

Public API (unchanged):
    build_executive_pdf(client_id, aws_account_id=None) -> bytes
"""

from io import BytesIO
from typing import Any, cast

from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from src.services.client_dashboard_service import ClientDashboardService
from src.services.client_stats_service import get_users_by_client, get_client_plan
from src.services.client_findings_service import ClientFindingsService
from src.models.aws_account import AWSAccount
from src.services.dashboard.governance_service import GovernanceService
from src.services.dashboard.risk_service import RiskService

from src.reports.client.executive_pdf.styles import build_styles
from src.reports.client.executive_pdf.sections import (
    build_header,
    build_info_row,
    build_financial_kpis,
    build_findings_cards,
    build_severity_section,
    build_governance_section,
    build_cost_trend_section,
    build_top_findings_section,
    build_service_breakdown_section,
    build_footer,
)


def build_executive_pdf(client_id: int, aws_account_id: int | None = None) -> bytes:
    # ── data ──────────────────────────────────────────────
    cost_data    = ClientDashboardService.get_cost_data(client_id, aws_account_id)
    stats_raw    = ClientFindingsService.get_stats(client_id, aws_account_id)
    plan         = get_client_plan(client_id) or "Sin plan activo"
    users        = get_users_by_client(client_id)
    accounts     = AWSAccount.query.filter_by(client_id=client_id, is_active=True).count()
    top_findings = ClientFindingsService.list_findings(
        client_id=client_id, page=1, per_page=5, status="active",
        severity=None, finding_type=None, service=None, region=None, search=None,
        sort_by="estimated_monthly_savings", sort_order="desc",
    ).get("data", [])

    try:
        gov  = GovernanceService.get_governance_score(client_id, aws_account_id)
        risk = RiskService.get_risk_profile(client_id, aws_account_id)
    except Exception:
        gov  = {"compliance_percentage": 0}
        risk = {"risk_level": "N/A", "risk_score": 0}

    service_breakdown: list[dict[str, Any]] = cast(
        list[dict[str, Any]], cost_data.get("service_breakdown", [])
    )
    service_bkdn: list[dict[str, Any]] = sorted(
        service_breakdown,
        key=lambda x: float(x.get("amount", 0)), reverse=True,
    )[:8]

    compliance  = float(gov.get("compliance_percentage", 0))
    risk_level  = str(risk.get("risk_level", "N/A")).upper()
    est_savings = float(stats_raw.get("estimated_monthly_savings", 0))

    account_label = "Todas las cuentas"
    if aws_account_id:
        acc = AWSAccount.query.get(aws_account_id)
        account_label = acc.account_name if acc else str(aws_account_id)

    # ── document ──────────────────────────────────────────
    buffer = BytesIO()
    margin = 1.8 * cm
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=margin, rightMargin=margin,
                               topMargin=margin, bottomMargin=margin)
    usable_w = A4[0] - 2 * margin
    styles   = build_styles()

    # ── assemble sections ─────────────────────────────────
    elements = []
    elements += build_header(styles, usable_w)
    elements += build_info_row(styles, plan, accounts, account_label, users)
    elements += build_financial_kpis(styles, usable_w, cost_data)
    elements += build_findings_cards(styles, usable_w, stats_raw)
    elements += build_severity_section(styles, usable_w, stats_raw)
    elements += build_governance_section(styles, usable_w, compliance, risk_level, est_savings)
    elements += build_cost_trend_section(styles, usable_w, cost_data.get("monthly_cost", []))
    elements += build_top_findings_section(styles, usable_w, top_findings)
    elements += build_service_breakdown_section(styles, usable_w, service_bkdn)
    elements += build_footer(styles)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

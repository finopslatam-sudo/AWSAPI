"""Función principal build_risk_pdf — ensambla el reporte de Riesgo & Compliance."""

from io import BytesIO

from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from src.services.client_stats_service import get_users_by_client, get_client_plan
from src.services.client_findings_service import ClientFindingsService
from src.services.dashboard.governance_service import GovernanceService
from src.services.dashboard.risk_service import RiskService
from src.models.aws_account import AWSAccount
from src.reports.client.risk.styles import build_styles, fmt_pct
from src.reports.client.risk.sections import (
    build_header,
    build_info_row,
    build_kpi_section,
    build_severity_chart,
    build_service_risk_section,
    build_high_findings_section,
    build_footer,
)


def build_risk_pdf(client_id: int, aws_account_id: int | None = None) -> bytes:
    # ── datos ──────────────────────────────────────────────────────────────────
    plan  = get_client_plan(client_id) or "Sin plan"
    users = get_users_by_client(client_id)
    acc_count = AWSAccount.query.filter_by(client_id=client_id, is_active=True).count()

    account_label = "Todas las cuentas"
    if aws_account_id:
        acc = AWSAccount.query.get(aws_account_id)
        account_label = acc.account_name if acc else str(aws_account_id)

    try:
        gov  = GovernanceService.get_governance_score(client_id, aws_account_id)
        risk = RiskService.get_risk_score(client_id, aws_account_id)
        risk_bkdn_raw = RiskService.get_risk_breakdown_by_service(client_id, aws_account_id)
        risk_bkdn = [{"service_name": svc, **data} for svc, data in risk_bkdn_raw.items()]
        risk_bkdn.sort(
            key=lambda x: x.get("high", 0) * 5 + x.get("medium", 0) * 3 + x.get("low", 0),
            reverse=True
        )
    except Exception:
        gov  = {"compliance_percentage": 0}
        risk = {"risk_level": "N/A", "risk_score": 0, "high": 0, "medium": 0, "low": 0}
        risk_bkdn = []

    stats = ClientFindingsService.get_stats(client_id, aws_account_id)
    high_findings = ClientFindingsService.list_findings(
        client_id=client_id, page=1, per_page=20, status="active", severity="HIGH",
        finding_type=None, service=None, region=None, search=None,
        sort_by="created_at", sort_order="desc",
    ).get("data", [])

    compliance  = float(gov.get("compliance_percentage", 0))
    risk_level  = str(risk.get("risk_level", "N/A")).upper()
    risk_score  = float(risk.get("risk_score", 0))
    high_cnt    = int(risk.get("high", 0))
    medium_cnt  = int(risk.get("medium", 0))
    low_cnt     = int(risk.get("low", 0))
    total_f     = int(stats.get("total", 0))
    active_f    = int(stats.get("active", 0))
    resolved_f  = int(stats.get("resolved", 0))

    compliance_label = "Óptimo" if compliance >= 80 else ("Requiere atención" if compliance >= 50 else "Crítico")
    compliance_fg    = "#16a34a" if compliance >= 80 else ("#d97706" if compliance >= 50 else "#dc2626")
    compliance_bg    = "#f0fdf4" if compliance >= 80 else ("#fffbeb" if compliance >= 50 else "#fef2f2")

    # ── documento ──────────────────────────────────────────────────────────────
    buffer = BytesIO()
    margin = 1.8 * cm
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=margin)
    usable_w = A4[0] - 2 * margin

    styles = build_styles(getSampleStyleSheet())

    el = []
    el += build_header(usable_w, styles)
    el += build_info_row(plan, acc_count, account_label, users, styles)
    el += build_kpi_section(
        risk_level, risk_score, compliance, compliance_label, compliance_fg,
        compliance_bg, high_cnt, medium_cnt, low_cnt, total_f, active_f, resolved_f,
        usable_w, styles,
    )
    el += build_severity_chart(high_cnt, medium_cnt, low_cnt, usable_w, styles)
    el += build_service_risk_section(risk_bkdn, styles)
    el += build_high_findings_section(high_findings, usable_w, styles)
    el += build_footer()

    doc.build(el)
    buffer.seek(0)
    return buffer.getvalue()

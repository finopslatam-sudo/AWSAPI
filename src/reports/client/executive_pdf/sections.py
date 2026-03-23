"""Re-exporta las secciones del PDF ejecutivo."""

from .header_section import build_header, build_info_row
from .financial_section import build_financial_kpis
from .findings_section import (
    build_findings_cards,
    build_severity_section,
    build_top_findings_section,
)
from .governance_section import build_governance_section
from .cost_sections import (
    build_cost_trend_section,
    build_service_breakdown_section,
)
from .footer_section import build_footer

__all__ = [
    "build_header",
    "build_info_row",
    "build_financial_kpis",
    "build_findings_cards",
    "build_severity_section",
    "build_top_findings_section",
    "build_governance_section",
    "build_cost_trend_section",
    "build_service_breakdown_section",
    "build_footer",
]

"""
INVENTORY XLSX REPORT — ENTERPRISE
====================================
Thin orchestrator.  All logic lives in the inventory_xlsx sub-package:
  · inventory_xlsx/styles.py   — fill/font/border constants
  · inventory_xlsx/helpers.py  — row writers, KPI block, conditional fills
  · inventory_xlsx/sheets.py   — one builder function per worksheet
"""

from io import BytesIO
from datetime import datetime

import pytz
from openpyxl import Workbook

from .inventory_xlsx.sheets import (
    build_summary_sheet,
    build_inventory_sheet,
    build_service_sheet,
    build_region_sheet,
    build_findings_sheet,
)


def build_inventory_xlsx(stats: dict) -> bytes:
    chile_tz  = pytz.timezone("America/Santiago")
    generated = datetime.now(chile_tz).strftime("%d/%m/%Y %H:%M CLT")

    resources      = stats.get("resources", [])
    by_service     = stats.get("by_service", {})
    by_region      = stats.get("by_region", {})
    by_state       = stats.get("by_state", {})
    total          = stats.get("total", 0)
    with_f         = stats.get("with_findings", 0)
    without_f      = stats.get("without_findings", 0)
    total_savings  = stats.get("total_savings", 0.0)
    active_f_count = stats.get("active_findings_count", 0)
    plan           = stats.get("plan", "—")
    users          = stats.get("user_count", 0)
    acc_count      = stats.get("account_count", 0)
    acc_label      = stats.get("account_label", "Todas las cuentas")

    wb  = Workbook()
    ws1 = wb.active

    build_summary_sheet(
        ws1,
        generated=generated, plan=plan, acc_count=acc_count, acc_label=acc_label,
        users=users, total=total, with_f=with_f, without_f=without_f,
        active_f_count=active_f_count, total_savings=total_savings,
        by_service=by_service, by_state=by_state, by_region=by_region,
    )
    build_inventory_sheet(wb, generated=generated, total=total, resources=resources)
    build_service_sheet(wb, generated=generated, total=total,
                        by_service=by_service, resources=resources)
    build_region_sheet(wb, generated=generated, total=total, by_region=by_region)
    build_findings_sheet(wb, generated=generated, total_savings=total_savings,
                         resources=resources)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

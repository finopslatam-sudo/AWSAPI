"""
INVENTORY STATS PROVIDER
========================
Reúne todos los datos necesarios para los reportes de Inventario de Recursos:
CSV y XLSX.
"""

from collections import defaultdict

from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.aws_finding import AWSFinding
from src.models.aws_account import AWSAccount
from src.services.client_stats_service import get_users_by_client, get_client_plan


def get_inventory_stats(client_id: int, aws_account_id: int | None = None) -> dict:

    # ── query base ────────────────────────────────────────────
    base_q = AWSResourceInventory.query.filter_by(
        client_id=client_id,
        is_active=True,
    )
    if aws_account_id:
        base_q = base_q.filter_by(aws_account_id=aws_account_id)

    resources = base_q.all()

    # ── findings activos para este cliente ────────────────────
    f_query = AWSFinding.query.filter_by(client_id=client_id, resolved=False)
    if aws_account_id:
        f_query = f_query.filter_by(aws_account_id=aws_account_id)

    active_findings = f_query.all()

    # resource_ids con findings activos → { resource_id: [findings] }
    findings_by_resource: dict[str, list] = defaultdict(list)
    for f in active_findings:
        findings_by_resource[f.resource_id].append(f)

    # ── cuentas para label ────────────────────────────────────
    accounts_map: dict[int, str] = {}
    for acc in AWSAccount.query.filter_by(client_id=client_id, is_active=True).all():
        accounts_map[acc.id] = acc.account_name or acc.account_id

    # ── agrupar por servicio ──────────────────────────────────
    by_service: dict[str, int] = defaultdict(int)
    for r in resources:
        by_service[r.service_name] += 1

    # ── agrupar por región ────────────────────────────────────
    by_region: dict[str, int] = defaultdict(int)
    for r in resources:
        key = r.region or "Sin región"
        by_region[key] += 1

    # ── agrupar por estado ────────────────────────────────────
    by_state: dict[str, int] = defaultdict(int)
    for r in resources:
        key = (r.state or "unknown").lower()
        by_state[key] += 1

    # ── con / sin hallazgos ───────────────────────────────────
    with_findings    = sum(1 for r in resources if r.resource_id in findings_by_resource)
    without_findings = len(resources) - with_findings

    # ── ahorros potenciales totales ───────────────────────────
    total_savings = sum(
        float(f.estimated_monthly_savings or 0)
        for f in active_findings
    )

    # ── detalle completo de recursos ─────────────────────────
    resource_rows = []
    for r in resources:
        flist = findings_by_resource.get(r.resource_id, [])
        max_sev = _max_severity(flist)
        est_sav = sum(float(f.estimated_monthly_savings or 0) for f in flist)

        resource_rows.append({
            "account_name":   accounts_map.get(r.aws_account_id, str(r.aws_account_id)),
            "service_name":   r.service_name,
            "resource_type":  r.resource_type,
            "resource_id":    r.resource_id,
            "region":         r.region or "—",
            "state":          r.state or "unknown",
            "tags":           _fmt_tags(r.tags),
            "metadata":       r.resource_metadata or {},
            "has_findings":   len(flist) > 0,
            "findings_count": len(flist),
            "max_severity":   max_sev,
            "est_savings":    round(est_sav, 2),
            "detected_at":    (r.detected_at.strftime("%Y-%m-%d") if r.detected_at else "—"),
            "last_seen_at":   (r.last_seen_at.strftime("%Y-%m-%d") if r.last_seen_at else "—"),
            "findings":       [
                {
                    "type":     f.finding_type,
                    "severity": f.severity,
                    "message":  f.message,
                    "savings":  float(f.estimated_monthly_savings or 0),
                }
                for f in flist
            ],
        })

    # ordena: primero con findings, luego por servicio
    resource_rows.sort(key=lambda x: (not x["has_findings"], x["service_name"]))

    return {
        "plan":            get_client_plan(client_id) or "Sin plan activo",
        "user_count":      get_users_by_client(client_id),
        "account_count":   len(accounts_map),
        "account_label":   accounts_map.get(aws_account_id, "Todas las cuentas") if aws_account_id else "Todas las cuentas",
        "total":           len(resources),
        "with_findings":   with_findings,
        "without_findings": without_findings,
        "active_findings_count": len(active_findings),
        "total_savings":   round(total_savings, 2),
        "by_service":      dict(sorted(by_service.items(), key=lambda x: -x[1])),
        "by_region":       dict(sorted(by_region.items(), key=lambda x: -x[1])),
        "by_state":        dict(sorted(by_state.items(), key=lambda x: -x[1])),
        "resources":       resource_rows,
    }


# ─────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────
_SEV_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def _max_severity(findings: list) -> str:
    if not findings:
        return "—"
    return max(findings, key=lambda f: _SEV_ORDER.get(f.severity.upper(), 0)).severity.upper()


def _fmt_tags(tags) -> str:
    if not tags:
        return "—"
    if isinstance(tags, dict):
        parts = [f"{k}={v}" for k, v in list(tags.items())[:5]]
        return "  |  ".join(parts)
    if isinstance(tags, list):
        parts = [f"{t.get('Key','?')}={t.get('Value','?')}" for t in tags[:5]]
        return "  |  ".join(parts)
    return str(tags)

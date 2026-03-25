"""
assistant_context_builder.py
Construye el contexto real del cliente para enviarlo a Finops.ia.
Lee datos de BD (findings, inventario, snapshots, cuentas) y genera
un bloque de texto que el modelo puede interpretar.
"""
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.risk_snapshot import RiskSnapshot
from src.models.aws_account import AWSAccount


def build_context(client_id: int, aws_account_id: int | None = None) -> str:
    lines: list[str] = ["=== DATOS REALES DEL CLIENTE ==="]

    # ── 1. Cuentas AWS ──────────────────────────────────────
    accounts = AWSAccount.query.filter_by(client_id=client_id, is_active=True).all()
    lines.append(f"\nCUENTAS AWS CONECTADAS: {len(accounts)}")
    for acc in accounts:
        sync = acc.last_sync.strftime("%Y-%m-%d") if acc.last_sync else "nunca"
        lines.append(f"  - {acc.account_name} (ID AWS: {acc.account_id}) | último sync: {sync}")

    # ── 2. Hallazgos activos ────────────────────────────────
    fq = AWSFinding.query.filter_by(client_id=client_id, resolved=False)
    if aws_account_id:
        fq = fq.filter_by(aws_account_id=aws_account_id)
    findings = fq.all()

    sev = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    svc_savings: dict[str, float] = {}
    total_savings = 0.0
    for f in findings:
        sev[f.severity] = sev.get(f.severity, 0) + 1
        s = float(f.estimated_monthly_savings or 0)
        total_savings += s
        svc_savings[f.aws_service] = svc_savings.get(f.aws_service, 0) + s

    lines.append(f"\nHALLAZGOS ACTIVOS (sin resolver): {len(findings)}")
    lines.append(f"  CRITICAL: {sev['CRITICAL']} | HIGH: {sev['HIGH']} | MEDIUM: {sev['MEDIUM']} | LOW: {sev['LOW']}")
    lines.append(f"  Ahorro potencial total: ${total_savings:.0f}/mes")

    if svc_savings:
        top_svcs = sorted(svc_savings.items(), key=lambda x: -x[1])[:5]
        lines.append("  Ahorro por servicio:")
        for svc, sv in top_svcs:
            lines.append(f"    - {svc}: ${sv:.0f}/mes")

    # Top 5 hallazgos por ahorro
    top5 = sorted(findings, key=lambda x: float(x.estimated_monthly_savings or 0), reverse=True)[:5]
    if top5:
        lines.append("\nTOP 5 HALLAZGOS POR AHORRO:")
        for f in top5:
            msg_short = f.message[:150] if f.message else ""
            lines.append(
                f"  [{f.severity}] {f.finding_type} | {f.resource_id} | "
                f"${float(f.estimated_monthly_savings or 0):.0f}/mes | {msg_short}"
            )

    # Hallazgos críticos
    criticals = [f for f in findings if f.severity == "CRITICAL"]
    if criticals:
        lines.append(f"\nHALLAZGOS CRÍTICOS ({len(criticals)}):")
        for f in criticals[:5]:
            lines.append(f"  - {f.finding_type} | {f.resource_id} | {f.region or 'N/A'}")

    # ── 3. Inventario ───────────────────────────────────────
    iq = AWSResourceInventory.query.filter_by(client_id=client_id, is_active=True)
    if aws_account_id:
        iq = iq.filter_by(aws_account_id=aws_account_id)

    svc_counts: dict[str, int] = {}
    region_set: set[str] = set()
    for r in iq.all():
        svc_counts[r.service_name] = svc_counts.get(r.service_name, 0) + 1
        if r.region:
            region_set.add(r.region)

    total_res = sum(svc_counts.values())
    lines.append(f"\nINVENTARIO: {total_res} recursos activos")
    for svc, cnt in sorted(svc_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  - {svc}: {cnt} recursos")
    if region_set:
        lines.append(f"  Regiones: {', '.join(sorted(region_set))}")

    # ── 4. Snapshots de riesgo ──────────────────────────────
    snaps = (
        RiskSnapshot.query
        .filter_by(client_id=client_id)
        .order_by(RiskSnapshot.created_at.desc())
        .limit(2)
        .all()
    )
    if snaps:
        cur = snaps[0]
        lines.append(f"\nRIESGO ACTUAL:")
        lines.append(f"  Score: {cur.risk_score} | Nivel: {cur.risk_level}")
        lines.append(f"  Health: {cur.health_score}/100 | Exposición: ${float(cur.financial_exposure or 0):.0f}")
        lines.append(f"  Gobernanza: {float(cur.governance_percentage or 0):.1f}%")
        if len(snaps) == 2:
            prev = snaps[1]
            d_score = float(cur.risk_score or 0) - float(prev.risk_score or 0)
            d_exp = float(cur.financial_exposure or 0) - float(prev.financial_exposure or 0)
            lines.append(
                f"  Cambio vs anterior: score {'+' if d_score >= 0 else ''}{d_score:.1f}, "
                f"exposición ${'+' if d_exp >= 0 else ''}{d_exp:.0f}"
            )

    lines.append("\n=== FIN DATOS DEL CLIENTE ===")
    return "\n".join(lines)

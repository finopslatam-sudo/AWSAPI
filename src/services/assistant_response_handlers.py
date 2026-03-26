"""
assistant_response_handlers.py
Handlers de respuesta para Finops.ia — uno por intención detectada.
Todos leen datos reales de la BD del cliente.
"""
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.risk_snapshot import RiskSnapshot
from src.models.aws_account import AWSAccount


# ── Helpers locales ───────────────────────────────────────────
def _findings(client_id, account_id=None):
    q = AWSFinding.query.filter_by(client_id=client_id, resolved=False)
    if account_id:
        q = q.filter_by(aws_account_id=account_id)
    return q.all()

def _inventory(client_id, account_id=None):
    q = AWSResourceInventory.query.filter_by(client_id=client_id, is_active=True)
    if account_id:
        q = q.filter_by(aws_account_id=account_id)
    return q.all()

def _snapshots(client_id, n=2):
    return (RiskSnapshot.query.filter_by(client_id=client_id)
            .order_by(RiskSnapshot.created_at.desc()).limit(n).all())

def _sav(f): return float(f.estimated_monthly_savings or 0)

def _account_lookup(client_id):
    return {a.id: (a.account_name, a.account_id)
            for a in AWSAccount.query.filter_by(client_id=client_id, is_active=True).all()}


# ── Handlers ─────────────────────────────────────────────────
def _h_greeting(client_id, account_id):
    fs = _findings(client_id, account_id)
    total_sav = sum(_sav(f) for f in fs)
    crits = sum(1 for f in fs if f.severity == "CRITICAL")
    snaps = _snapshots(client_id, 1)
    risk = f"Score: {snaps[0].risk_score} ({snaps[0].risk_level})" if snaps else "Sin datos de riesgo aún"
    return (
        f"Hola, soy Finops.ia — Tu asistente AWS especializado en FinOps.\n\n"
        f"Resumen de tu cuenta:\n"
        f"  • {len(fs)} hallazgos activos ({crits} críticos)\n"
        f"  • Ahorro potencial: ${total_sav:.0f}/mes\n"
        f"  • {risk}\n\n"
        f"Usa los botones de abajo o escríbeme directamente."
    )

def _h_account_info(client_id, account_id):
    accounts = AWSAccount.query.filter_by(client_id=client_id, is_active=True).all()
    if not accounts:
        return "No tienes cuentas AWS conectadas actualmente."
    lines = [f"Tienes {len(accounts)} cuenta(s) AWS conectada(s):\n"]
    for acc in accounts:
        sync = acc.last_sync.strftime("%Y-%m-%d %H:%M") if acc.last_sync else "nunca"
        lines.append(f"  • {acc.account_name} | Account ID: {acc.account_id}")
        lines.append(f"    Último escaneo: {sync} | Estado: {'activa' if acc.is_active else 'inactiva'}")
    if account_id:
        active = next((a for a in accounts if a.id == account_id), None)
        if active:
            lines.append(f"\nFiltrando actualmente por: {active.account_name} ({active.account_id})")
        else:
            lines.append("\nActualmente mostrando datos de todas las cuentas.")
    else:
        lines.append("\nActualmente mostrando datos de todas las cuentas combinadas.")
    return "\n".join(lines)

def _h_savings_total(client_id, account_id):
    fs = _findings(client_id, account_id)
    if not fs:
        return "No hay hallazgos activos con ahorro estimado."
    total = sum(_sav(f) for f in fs)
    by_svc = {}
    for f in fs:
        by_svc[f.aws_service] = by_svc.get(f.aws_service, 0) + _sav(f)
    lines = [f"Ahorro potencial total: ${total:.0f}/mes (${total*12:.0f}/año)\n", "Por servicio:"]
    for s, v in sorted(by_svc.items(), key=lambda x: -x[1])[:6]:
        lines.append(f"  • {s}: ${v:.0f}/mes")
    top3 = sorted(fs, key=_sav, reverse=True)[:3]
    lines.append("\nTop 3 oportunidades:")
    for f in top3:
        lines.append(f"  • [{f.severity}] {f.finding_type} — ${_sav(f):.0f}/mes")
    return "\n".join(lines)

def _h_why_increase(client_id, account_id):
    snaps = _snapshots(client_id, 2)
    fs = _findings(client_id, account_id)
    lines = []
    if len(snaps) == 2:
        cur, prev = snaps
        d_exp = float(cur.financial_exposure or 0) - float(prev.financial_exposure or 0)
        d_f = (cur.total_findings or 0) - (prev.total_findings or 0)
        arrow = "subió" if d_exp > 0 else "bajó"
        lines.append(f"La exposición financiera {arrow} ${abs(d_exp):.0f} vs el snapshot anterior.")
        if d_f != 0:
            lines.append(f"  • Hallazgos: {'+'if d_f>0 else ''}{d_f} vs anterior")
    by_svc = {}
    for f in fs:
        by_svc[f.aws_service] = by_svc.get(f.aws_service, 0) + _sav(f)
    if by_svc:
        lines.append("\nPrincipales servicios con costo optimizable:")
        for s, v in sorted(by_svc.items(), key=lambda x: -x[1])[:4]:
            lines.append(f"  • {s}: ${v:.0f}/mes sin optimizar")
    return "\n".join(lines) if lines else "No hay suficientes datos. Ejecuta un escaneo."

def _h_critical(client_id, account_id):
    fs = [f for f in _findings(client_id, account_id) if f.severity == "CRITICAL"]
    if not fs:
        return "No tienes hallazgos CRITICAL activos."
    accs = _account_lookup(client_id)
    lines = [f"{len(fs)} hallazgos CRITICAL:\n"]
    for f in fs[:7]:
        a_name, a_id = accs.get(f.aws_account_id, ("?", "?"))
        lines.append(f"  • {f.finding_type} | {f.resource_id} | {f.region or 'N/A'}")
        lines.append(f"    Cuenta: {a_name} ({a_id})")
        lines.append(f"    {(f.message or '')[:120]}")
        lines.append(f"    Ahorro: ${_sav(f):.0f}/mes\n")
    return "\n".join(lines)

def _h_unused(client_id, account_id):
    idle_kw = ["IDLE", "UNDERUTILIZED", "UNUSED", "NAT_IDLE"]
    fs = [f for f in _findings(client_id, account_id) if any(k in f.finding_type.upper() for k in idle_kw)]
    if not fs:
        return "No se detectaron recursos claramente sin usar."
    accs = _account_lookup(client_id)
    total = sum(_sav(f) for f in fs)
    lines = [f"{len(fs)} recursos sin usar / subutilizados | ${total:.0f}/mes\n"]
    for f in fs[:6]:
        a_name, a_id = accs.get(f.aws_account_id, ("?", "?"))
        lines.append(f"  • [{f.aws_service}] {f.resource_id} — ${_sav(f):.0f}/mes")
        lines.append(f"    Cuenta: {a_name} ({a_id})")
        lines.append(f"    {(f.message or '')[:100]}")
    return "\n".join(lines)

def _h_risk(client_id, account_id):
    snaps = _snapshots(client_id, 2)
    if not snaps:
        return "No hay datos de riesgo. Ejecuta un escaneo primero."
    cur = snaps[0]
    lines = [
        f"Nivel de riesgo: {cur.risk_level} (score: {cur.risk_score})\n",
        f"  • Health score: {cur.health_score}/100",
        f"  • Exposición financiera: ${float(cur.financial_exposure or 0):.0f}",
        f"  • Gobernanza: {float(cur.governance_percentage or 0):.1f}%",
        f"  • Hallazgos: {cur.total_findings} (HIGH:{cur.high_count} MED:{cur.medium_count} LOW:{cur.low_count})",
    ]
    if len(snaps) == 2:
        d = float(cur.risk_score or 0) - float(snaps[1].risk_score or 0)
        lines.append(f"\n  Tendencia: score {'+' if d>=0 else ''}{d:.1f} vs snapshot anterior")
    return "\n".join(lines)

def _h_services(client_id, account_id):
    inv = _inventory(client_id, account_id)
    if not inv:
        return "No hay inventario. Ejecuta un escaneo."
    counts = {}
    for r in inv:
        counts[r.service_name] = counts.get(r.service_name, 0) + 1
    lines = [f"{sum(counts.values())} recursos en {len(counts)} servicios:\n"]
    for s, c in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"  • {s}: {c}")
    return "\n".join(lines)

def _h_expensive(client_id, account_id):
    top = sorted(_findings(client_id, account_id), key=_sav, reverse=True)[:8]
    if not top:
        return "No hay hallazgos con estimación de ahorro."
    accs = _account_lookup(client_id)
    lines = ["Recursos con mayor impacto en costos:\n"]
    for f in top:
        a_name, a_id = accs.get(f.aws_account_id, ("?", "?"))
        lines.append(f"  • [{f.severity}] {f.resource_id} | {f.aws_service}")
        lines.append(f"    Cuenta: {a_name} ({a_id})")
        lines.append(f"    {(f.message or '')[:100]}")
        lines.append(f"    Ahorro: ${_sav(f):.0f}/mes\n")
    return "\n".join(lines)

def _h_changes(client_id, account_id):
    snaps = _snapshots(client_id, 2)
    if len(snaps) < 2:
        return "Solo hay un snapshot disponible. Se necesitan al menos dos para comparar."
    cur, prev = snaps
    def d(a, b): return float(a or 0) - float(b or 0)
    lines = ["Comparación vs snapshot anterior:\n",
             f"  • Score riesgo: {d(cur.risk_score, prev.risk_score):+.1f}",
             f"  • Exposición: ${d(cur.financial_exposure, prev.financial_exposure):+.0f}",
             f"  • Health score: {d(cur.health_score, prev.health_score):+.0f} pts",
             f"  • Hallazgos: {int(d(cur.total_findings, prev.total_findings)):+d}"]
    return "\n".join(lines)

def _h_regions(client_id, account_id):
    inv = _inventory(client_id, account_id)
    reg = {}
    for r in inv:
        if r.region:
            reg[r.region] = reg.get(r.region, 0) + 1
    if not reg:
        return "No hay datos de regiones en el inventario."
    lines = [f"Recursos en {len(reg)} región(es):\n"]
    for region, cnt in sorted(reg.items()):
        lines.append(f"  • {region}: {cnt} recursos")
    return "\n".join(lines)

def _h_resolve_first(client_id, account_id):
    SEV = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    priority = sorted(_findings(client_id, account_id),
                      key=lambda f: (SEV.get(f.severity, 0), _sav(f)),
                      reverse=True)[:6]
    if not priority:
        return "No hay hallazgos pendientes."
    accs = _account_lookup(client_id)
    lines = ["Prioridad de resolución (severidad + ahorro):\n"]
    for i, f in enumerate(priority, 1):
        a_name, a_id = accs.get(f.aws_account_id, ("?", "?"))
        lines.append(f"  {i}. [{f.severity}] {f.finding_type} | ${_sav(f):.0f}/mes")
        lines.append(f"     {f.resource_id} | {a_name} ({a_id})")
    return "\n".join(lines)

def _h_service_findings(client_id, account_id, service_name: str):
    fs = [f for f in _findings(client_id, account_id) if f.aws_service == service_name]
    if not fs:
        return f"No hay hallazgos de {service_name} activos."
    accs = _account_lookup(client_id)
    total = sum(_sav(f) for f in fs)
    lines = [f"{len(fs)} hallazgos {service_name} | ${total:.0f}/mes de ahorro potencial\n"]
    for f in fs[:5]:
        a_name, a_id = accs.get(f.aws_account_id, ("?", "?"))
        lines.append(f"  • {f.resource_id}")
        lines.append(f"    Cuenta: {a_name} ({a_id})")
        lines.append(f"    {(f.message or '')[:150]}")
        lines.append(f"    Ahorro: ${_sav(f):.0f}/mes\n")
    return "\n".join(lines)

def _h_savings_plans(client_id, account_id):
    inv = _inventory(client_id, account_id)
    ec2 = sum(1 for r in inv if r.service_name == "EC2")
    lmb = sum(1 for r in inv if r.service_name == "Lambda")
    lines = [f"Análisis Savings Plans:\n  • EC2 activos: {ec2}  • Lambda activas: {lmb}\n"]
    if ec2 >= 3:
        lines.append(f"Con {ec2} instancias EC2, Compute Savings Plans puede generar hasta 66% de descuento.")
        lines.append("Recomendación: evalúa compromiso de 1 año para máxima flexibilidad.")
    elif ec2 > 0:
        lines.append("Pocas instancias: evalúa Reserved Instances para workloads estables.")
    if lmb >= 5:
        lines.append(f"\nCon {lmb} funciones Lambda, Compute Savings Plans también aplica.")
    return "\n".join(lines)

def _h_all_findings(client_id, account_id):
    fs = _findings(client_id, account_id)
    if not fs:
        return "No hay hallazgos activos."
    sev = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    by_type = {}
    for f in fs:
        sev[f.severity] = sev.get(f.severity, 0) + 1
        by_type[f.finding_type] = by_type.get(f.finding_type, 0) + 1
    total = sum(_sav(f) for f in fs)
    lines = [f"{len(fs)} hallazgos | ${total:.0f}/mes ahorro total\n",
             f"  CRITICAL:{sev['CRITICAL']} HIGH:{sev['HIGH']} MEDIUM:{sev['MEDIUM']} LOW:{sev['LOW']}\n",
             "Por tipo:"]
    for t, c in sorted(by_type.items(), key=lambda x: -x[1])[:10]:
        lines.append(f"  • {t}: {c}")
    return "\n".join(lines)

def _h_health(client_id, account_id):
    snaps = _snapshots(client_id, 1)
    if not snaps:
        return "No hay datos de health disponibles."
    cur = snaps[0]
    h, g = cur.health_score or 0, float(cur.governance_percentage or 0)
    h_msg = ("Prioriza resolver hallazgos CRITICAL y HIGH." if h < 50
             else "Hay margen de mejora." if h < 75 else "Buen nivel.")
    g_msg = ("Muchos recursos sin etiquetas. Revisa tu política de tagging." if g < 50
             else "Mejora el etiquetado." if g < 80 else "Recursos bien etiquetados.")
    return f"Health score: {h}/100 — {h_msg}\nGobernanza: {g:.1f}% — {g_msg}"

# ── Registro de handlers ─────────────────────────────────────
_HANDLERS = {
    "account_info":     _h_account_info,
    "savings_total":    _h_savings_total,
    "why_increase":     _h_why_increase,
    "critical_findings": _h_critical,
    "unused_resources": _h_unused,
    "risk_level":       _h_risk,
    "services_in_use":  _h_services,
    "most_expensive":   _h_expensive,
    "changes_previous": _h_changes,
    "regions":          _h_regions,
    "resolve_first":    _h_resolve_first,
    "ec2_cost":         lambda cid, aid: _h_service_findings(cid, aid, "EC2"),
    "rds_findings":     lambda cid, aid: _h_service_findings(cid, aid, "RDS"),
    "lambda_findings":  lambda cid, aid: _h_service_findings(cid, aid, "Lambda"),
    "s3_findings":      lambda cid, aid: _h_service_findings(cid, aid, "S3"),
    "savings_plans":    _h_savings_plans,
    "all_findings":     _h_all_findings,
    "health":           _h_health,
}

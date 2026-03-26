"""
assistant_response_handlers_extra.py
Handlers adicionales para Finops.ia — nuevos intents de análisis y recomendaciones.
"""
from src.models.aws_finding import AWSFinding
from src.services.assistant_response_handlers import _findings, _sav, _account_lookup


def _h_account_spending(client_id, _account_id):
    all_fs = AWSFinding.query.filter_by(client_id=client_id, resolved=False).all()
    if not all_fs:
        return "No hay hallazgos activos para comparar cuentas."
    accs = _account_lookup(client_id)
    by_acc = {}
    for f in all_fs:
        key = f.aws_account_id
        if key not in by_acc:
            by_acc[key] = {"savings": 0, "findings": 0}
        by_acc[key]["savings"] += _sav(f)
        by_acc[key]["findings"] += 1
    sorted_accs = sorted(by_acc.items(), key=lambda x: -x[1]["savings"])
    lines = ["Ahorro potencial por cuenta AWS (mayor a menor):\n"]
    for i, (acc_db_id, data) in enumerate(sorted_accs, 1):
        a_name, a_aws_id = accs.get(acc_db_id, ("Cuenta desconocida", "?"))
        lines.append(f"  {i}. {a_name} ({a_aws_id})")
        lines.append(f"     Ahorro potencial: ${data['savings']:.0f}/mes | {data['findings']} hallazgos")
    total = sum(d["savings"] for d in by_acc.values())
    lines.append(f"\nTotal combinado: ${total:.0f}/mes (${total * 12:.0f}/año)")
    return "\n".join(lines)


def _h_recommend_eliminate(client_id, account_id):
    idle_kw = ["IDLE", "UNUSED", "NAT_IDLE", "UNDERUTILIZED"]
    all_fs = _findings(client_id, account_id)
    idle_fs = sorted(
        [f for f in all_fs if any(k in f.finding_type.upper() for k in idle_kw)],
        key=_sav, reverse=True
    )
    if not idle_fs:
        return "No se detectaron recursos claramente sin usar para eliminar."
    accs = _account_lookup(client_id)
    total = sum(_sav(f) for f in idle_fs)
    lines = [f"{len(idle_fs)} recurso(s) candidatos a eliminación | ${total:.0f}/mes de ahorro:\n"]
    for f in idle_fs[:6]:
        a_name, a_id = accs.get(f.aws_account_id, ("?", "?"))
        lines.append(f"  • [{f.aws_service}] {f.resource_id}")
        lines.append(f"    Cuenta: {a_name} ({a_id})")
        lines.append(f"    {(f.message or '')[:120]}")
        lines.append(f"    Ahorro si se elimina: ${_sav(f):.0f}/mes\n")
    return "\n".join(lines)


def _h_service_most_expensive(client_id, account_id):
    fs = _findings(client_id, account_id)
    if not fs:
        return "No hay hallazgos activos."
    accs = _account_lookup(client_id)
    by_svc = {}
    for f in fs:
        by_svc[f.aws_service] = by_svc.get(f.aws_service, 0) + _sav(f)
    sorted_svcs = sorted(by_svc.items(), key=lambda x: -x[1])
    lines = ["Servicios ordenados por ahorro potencial (mayor a menor):\n"]
    for svc, total in sorted_svcs:
        svc_fs = [f for f in fs if f.aws_service == svc]
        acc_names = list({accs.get(f.aws_account_id, ("?", "?"))[0] for f in svc_fs})
        lines.append(f"  • {svc}: ${total:.0f}/mes — en: {', '.join(acc_names[:3])}")
    top_svc, top_val = sorted_svcs[0]
    lines.append(f"\nServicio con mayor impacto: {top_svc} (${top_val:.0f}/mes)")
    return "\n".join(lines)


def _h_service_least_expensive(client_id, account_id):
    fs = _findings(client_id, account_id)
    if not fs:
        return "No hay hallazgos activos."
    by_svc = {}
    for f in fs:
        by_svc[f.aws_service] = by_svc.get(f.aws_service, 0) + _sav(f)
    if not by_svc:
        return "No hay datos de servicios con hallazgos."
    sorted_svcs = sorted(by_svc.items(), key=lambda x: x[1])
    lines = ["Servicios con menor ahorro potencial detectado:\n"]
    for svc, total in sorted_svcs[:4]:
        lines.append(f"  • {svc}: ${total:.0f}/mes")
    lines.append(
        "\nNota: menor ahorro potencial indica que el servicio está bien optimizado "
        "o tiene pocos hallazgos activos."
    )
    return "\n".join(lines)


def _h_best_opportunity(client_id, account_id):
    fs = _findings(client_id, account_id)
    if not fs:
        return "No hay hallazgos activos."
    accs = _account_lookup(client_id)
    best = max(fs, key=_sav)
    a_name, a_id = accs.get(best.aws_account_id, ("?", "?"))
    lines = [
        "Mejor oportunidad de ahorro:\n",
        f"  Tipo:     {best.finding_type}",
        f"  Recurso:  {best.resource_id}",
        f"  Servicio: {best.aws_service} | Región: {best.region or 'N/A'}",
        f"  Cuenta:   {a_name} ({a_id})",
        f"  Severidad:{best.severity}",
        f"  Ahorro:   ${_sav(best):.0f}/mes (${_sav(best) * 12:.0f}/año)",
        f"\n  Acción: {(best.message or 'Revisa este recurso')[:200]}",
    ]
    top3 = sorted(fs, key=_sav, reverse=True)[:3]
    if len(top3) > 1:
        lines.append("\nOtras oportunidades top:")
        for f in top3[1:]:
            a = accs.get(f.aws_account_id, ("?", "?"))
            lines.append(f"  • {f.finding_type} | {a[0]} ({a[1]}) | ${_sav(f):.0f}/mes")
    return "\n".join(lines)


def _h_reduce_spending(client_id, account_id):
    fs = _findings(client_id, account_id)
    if not fs:
        return "No hay hallazgos activos. Tu infraestructura parece optimizada."
    accs = _account_lookup(client_id)
    idle_kw = ["IDLE", "UNUSED", "NAT_IDLE"]
    idle_fs = [f for f in fs if any(k in f.finding_type.upper() for k in idle_kw)]
    right_fs = [f for f in fs if "RIGHTSIZE" in f.finding_type.upper() or "DOWNSIZE" in f.finding_type.upper()]
    crit_fs = [f for f in fs if f.severity == "CRITICAL"]
    lines = ["Plan de acción para reducir costos:\n"]
    step = 1
    if crit_fs:
        total_c = sum(_sav(f) for f in crit_fs)
        lines.append(f"  {step}. Resolver {len(crit_fs)} hallazgos CRITICAL (${total_c:.0f}/mes)")
        for f in sorted(crit_fs, key=_sav, reverse=True)[:3]:
            a = accs.get(f.aws_account_id, ("?", "?"))
            lines.append(f"     → {f.resource_id} | {a[0]} ({a[1]})")
        step += 1
    if idle_fs:
        total_i = sum(_sav(f) for f in idle_fs)
        lines.append(f"\n  {step}. Eliminar {len(idle_fs)} recursos sin usar (${total_i:.0f}/mes)")
        for f in sorted(idle_fs, key=_sav, reverse=True)[:3]:
            a = accs.get(f.aws_account_id, ("?", "?"))
            lines.append(f"     → {f.aws_service} {f.resource_id} | {a[0]} ({a[1]})")
        step += 1
    if right_fs:
        total_r = sum(_sav(f) for f in right_fs)
        lines.append(f"\n  {step}. Hacer rightsizing de {len(right_fs)} recursos (${total_r:.0f}/mes)")
        step += 1
    total = sum(_sav(f) for f in fs)
    lines.append(f"\nAhorro total si implementas todo: ${total:.0f}/mes (${total * 12:.0f}/año)")
    return "\n".join(lines)


# ── Registro de handlers extra ────────────────────────────────
_HANDLERS_EXTRA = {
    "account_spending":       _h_account_spending,
    "recommend_eliminate":    _h_recommend_eliminate,
    "service_most_expensive": _h_service_most_expensive,
    "service_least_expensive": _h_service_least_expensive,
    "best_opportunity":       _h_best_opportunity,
    "reduce_spending":        _h_reduce_spending,
}

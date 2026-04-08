"""
ALERT EVALUATORS
================
Funciones de evaluación para cada tipo de política de alerta.
Cada evaluador recibe un AlertPolicy y retorna (fired: bool, context: dict).
"""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from src.models.alert_policy import AlertPolicy
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.services.cost_explorer_cache_service import CostExplorerCacheService as CostExplorerService
from src.aws.anomaly_monitor_service import AnomalyMonitorService


# ── HELPERS COMPARTIDOS ───────────────────────────────────────────────────────

def _get_accounts(policy: AlertPolicy) -> list:
    from src.models.aws_account import AWSAccount
    if policy.aws_account_id:
        account = AWSAccount.query.filter_by(
            id=policy.aws_account_id,
            client_id=policy.client_id,
            is_active=True
        ).first()
        return [account] if account else []
    return AWSAccount.query.filter_by(client_id=policy.client_id, is_active=True).all()


def _monthly_cost(account) -> float:
    try:
        months = CostExplorerService(account).get_last_6_months_cost()
        return months[-1]["amount"] if months else 0.0
    except Exception:
        return 0.0


def _annual_cost(account) -> float:
    try:
        data = CostExplorerService(account).get_annual_costs()
        return data.get("current_year_ytd", 0.0)
    except Exception:
        return 0.0


def _annual_previous_cost(account) -> float:
    try:
        data = CostExplorerService(account).get_annual_costs()
        return data.get("previous_year_cost", 0.0)
    except Exception:
        return 0.0


def _monthly_reference_avg(accounts: list) -> float:
    """
    Referencia para comparaciones porcentuales mensuales:
    promedio de los últimos 3 meses (sin incluir el mes actual),
    agregado sobre todas las cuentas.
    """
    reference = 0.0
    for account in accounts:
        try:
            months = CostExplorerService(account).get_last_6_months_cost()
            past = [m["amount"] for m in months[:-1][-3:] if m["amount"] > 0]
            if past:
                reference += (sum(past) / len(past))
        except Exception:
            pass
    return reference


def _exceeds(value: float, threshold: float, t_type: str, reference: float = 0.0) -> bool:
    if t_type == "USD":
        return value >= threshold
    if t_type == "%" and reference > 0:
        return (value / reference * 100) >= threshold
    return False


# ── EVALUADORES ───────────────────────────────────────────────────────────────

def evaluate_budget_monthly(policy: AlertPolicy):
    accounts = _get_accounts(policy)
    total = sum(_monthly_cost(a) for a in accounts)
    threshold = policy.threshold or 0
    t_type = policy.threshold_type or "USD"
    reference = _monthly_reference_avg(accounts) if t_type == "%" else 0.0

    fired = _exceeds(total, threshold, t_type, reference)
    context = {
        "costo_actual_mes": f"USD {round(total, 2)}",
        "umbral": f"{threshold} {t_type}",
        "periodo": "Mensual",
    }
    if t_type == "%":
        context["referencia_ult_3_meses"] = f"USD {round(reference, 2)}"
    return fired, context


def evaluate_budget_annual(policy: AlertPolicy):
    accounts = _get_accounts(policy)
    total = sum(_annual_cost(a) for a in accounts)
    reference = sum(_annual_previous_cost(a) for a in accounts)
    threshold = policy.threshold or 0
    t_type = policy.threshold_type or "USD"

    fired = _exceeds(total, threshold, t_type, reference)
    context = {
        "costo_acumulado_año": f"USD {round(total, 2)}",
        "umbral": f"{threshold} {t_type}",
        "periodo": "Anual",
    }
    if t_type == "%":
        context["referencia_año_anterior"] = f"USD {round(reference, 2)}"
    return fired, context


def evaluate_anomaly_spike(policy: AlertPolicy):
    accounts = _get_accounts(policy)
    if not accounts:
        return False, {}

    threshold = policy.threshold or 10
    t_type = policy.threshold_type or "USD"
    min_impact = threshold if t_type == "USD" else 10.0

    all_anomalies = []
    for account in accounts:
        anomalies = AnomalyMonitorService.get_anomalies(account, min_impact_usd=min_impact)
        all_anomalies.extend(anomalies)

    if all_anomalies:
        detalle = [
            {
                "cuenta": a["cuenta"],
                "impacto": f"USD {a['impacto_usd']}",
                "esperado": f"USD {a['gasto_esperado_usd']}",
                "servicios": ", ".join(a["servicios"]) if a["servicios"] else "N/A",
                "desde": a["fecha_inicio"],
            }
            for a in all_anomalies[:5]
        ]
        return True, {
            "anomalias_detectadas": len(all_anomalies),
            "detalle": detalle,
            "fuente": "AWS Cost Anomaly Detection (ML nativo)",
        }

    try:
        months = CostExplorerService(accounts[0]).get_last_6_months_cost()
        if len(months) < 2:
            return False, {}
        current = months[-1]["amount"]
        previous = months[-2]["amount"]
        if previous <= 0:
            return False, {}
        increase_pct = ((current - previous) / previous) * 100
        pct_threshold = threshold if t_type == "%" else 20
        fired = increase_pct >= pct_threshold
        return fired, {
            "costo_mes_actual": f"USD {round(current, 2)}",
            "costo_mes_anterior": f"USD {round(previous, 2)}",
            "incremento": f"{round(increase_pct, 1)}%",
            "umbral_alerta": f"{pct_threshold}% de incremento",
            "fuente": "Cálculo manual (monitor AWS pendiente)",
        }
    except Exception:
        return False, {}


def evaluate_service_cost(policy: AlertPolicy):
    accounts = _get_accounts(policy)
    threshold = policy.threshold or 0
    over = []
    for account in accounts:
        try:
            breakdown = CostExplorerService(account).get_service_breakdown_current_month()
            for svc in breakdown:
                if svc["amount"] >= threshold:
                    over.append({"servicio": svc["service"], "costo": f"USD {round(svc['amount'], 2)}"})
        except Exception:
            pass
    fired = len(over) > 0
    return fired, {
        "servicios_sobre_umbral": over[:5],
        "umbral_por_servicio": f"USD {threshold}",
    }


def evaluate_tagging_policy(policy: AlertPolicy):
    q = AWSResourceInventory.query.filter_by(client_id=policy.client_id, is_active=True)
    if policy.aws_account_id:
        q = q.filter_by(aws_account_id=policy.aws_account_id)
    resources = q.all()
    untagged = [r for r in resources if not r.tags or r.tags == {}]
    threshold = int(policy.threshold or 1)
    fired = len(untagged) >= threshold
    return fired, {
        "recursos_sin_etiquetas": len(untagged),
        "total_recursos": len(resources),
        "umbral": threshold,
    }


def evaluate_idle_resources(policy: AlertPolicy):
    idle_types = ["idle", "rightsizing", "underutilized", "unused", "low_utilization"]
    q = AWSFinding.query.filter_by(client_id=policy.client_id, resolved=False)
    if policy.aws_account_id:
        q = q.filter_by(aws_account_id=policy.aws_account_id)
    findings = q.all()
    idle = [f for f in findings if any(t in f.finding_type.lower() for t in idle_types)]
    threshold = int(policy.threshold or 1)
    fired = len(idle) >= threshold
    return fired, {
        "recursos_inactivos_detectados": len(idle),
        "umbral": threshold,
        "ahorro_potencial": f"USD {sum(float(f.estimated_monthly_savings or 0) for f in idle):.2f}",
    }


def evaluate_forecast(policy: AlertPolicy):
    accounts = _get_accounts(policy)
    if not accounts:
        return False, {}
    try:
        months = CostExplorerService(accounts[0]).get_last_6_months_cost()
        if not months:
            return False, {}
        current_cost = months[-1]["amount"]
        today = date.today()
        days_elapsed = today.day
        if days_elapsed <= 0:
            return False, {}
        next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        days_in_month = (next_month - timedelta(days=1)).day
        projected = (current_cost / days_elapsed) * days_in_month
        threshold = policy.threshold or 0
        t_type = policy.threshold_type or "USD"
        reference = _monthly_reference_avg(accounts) if t_type == "%" else 0.0
        fired = _exceeds(projected, threshold, t_type, reference)
        context = {
            "proyeccion_fin_de_mes": f"USD {round(projected, 2)}",
            "gasto_actual": f"USD {round(current_cost, 2)}",
            "dias_transcurridos": days_elapsed,
            "umbral": f"{threshold} {t_type}",
        }
        if t_type == "%":
            context["referencia_ult_3_meses"] = f"USD {round(reference, 2)}"
        return fired, context
    except Exception:
        return False, {}


def evaluate_off_hours(policy: AlertPolicy):
    tz = ZoneInfo("America/Santiago")
    from datetime import datetime
    hour = datetime.now(tz).hour
    is_off = hour >= 22 or hour < 8
    if not is_off:
        return False, {"razon": "Dentro de horario hábil (08:00–22:00 CL)"}
    q = AWSResourceInventory.query.filter_by(client_id=policy.client_id, is_active=True)
    if policy.aws_account_id:
        q = q.filter_by(aws_account_id=policy.aws_account_id)
    running = q.filter(AWSResourceInventory.state.in_(["running", "available"])).all()
    threshold = int(policy.threshold or 1)
    fired = len(running) >= threshold
    return fired, {
        "recursos_activos_fuera_horario": len(running),
        "hora_actual_cl": f"{hour:02d}:00",
        "umbral": threshold,
    }


def evaluate_lifecycle(policy: AlertPolicy):
    lifecycle_types = ["snapshot", "lifecycle", "stale", "orphan", "unattached", "old_"]
    q = AWSFinding.query.filter_by(client_id=policy.client_id, resolved=False)
    if policy.aws_account_id:
        q = q.filter_by(aws_account_id=policy.aws_account_id)
    findings = q.all()
    lc = [f for f in findings if any(t in f.finding_type.lower() for t in lifecycle_types)]
    threshold = int(policy.threshold or 1)
    fired = len(lc) >= threshold
    return fired, {
        "recursos_con_alerta_ciclo_vida": len(lc),
        "umbral": threshold,
    }

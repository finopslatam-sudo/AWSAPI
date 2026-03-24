"""
ALERT ENGINE
============

Evaluador de políticas de alerta.
Se ejecuta periódicamente (cron) y dispara notificaciones
cuando se cumplen las condiciones configuradas.

Políticas soportadas:
- budget-monthly   → gasto mensual vs umbral
- budget-annual    → gasto anual vs umbral
- anomaly-spike    → incremento % vs mes anterior
- service-cost     → algún servicio AWS supera umbral
- tagging-policy   → recursos sin etiquetas
- idle-resources   → findings de recursos inactivos
- forecast         → proyección fin de mes vs umbral
- off-hours        → recursos activos en horario no hábil
- lifecycle        → findings de ciclo de vida pendientes
"""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from src.models.alert_policy import AlertPolicy
from src.models.aws_account import AWSAccount
from src.models.aws_finding import AWSFinding
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.database import db
from src.aws.cost_explorer_service import CostExplorerService
from src.services.alert_notifier import dispatch_alert


# ── COOLDOWN POR PERÍODO ──────────────────────────────────────────

PERIOD_MIN_HOURS = {
    "daily":   23,
    "weekly":  167,
    "monthly": 719,
    "annual":  8759,
}


def _should_fire(policy: AlertPolicy) -> bool:
    if not policy.last_fired_at:
        return True
    min_hours = PERIOD_MIN_HOURS.get(policy.period or "daily", 23)
    elapsed = (datetime.utcnow() - policy.last_fired_at).total_seconds() / 3600
    return elapsed >= min_hours


def _mark_fired(policy: AlertPolicy):
    policy.last_fired_at = datetime.utcnow()
    db.session.commit()


# ── HELPERS ───────────────────────────────────────────────────────

def _get_accounts(policy: AlertPolicy) -> list:
    if policy.aws_account_id:
        account = AWSAccount.query.filter_by(
            id=policy.aws_account_id,
            client_id=policy.client_id,
            is_active=True
        ).first()
        return [account] if account else []
    return AWSAccount.query.filter_by(
        client_id=policy.client_id,
        is_active=True
    ).all()


def _monthly_cost(account: AWSAccount) -> float:
    try:
        months = CostExplorerService(account).get_last_6_months_cost()
        return months[-1]["amount"] if months else 0.0
    except Exception:
        return 0.0


def _annual_cost(account: AWSAccount) -> float:
    try:
        data = CostExplorerService(account).get_annual_costs()
        return data.get("current_year_ytd", 0.0)
    except Exception:
        return 0.0


def _exceeds(value: float, threshold: float, t_type: str, reference: float = 0.0) -> bool:
    if t_type == "USD":
        return value >= threshold
    if t_type == "%" and reference > 0:
        return (value / reference * 100) >= threshold
    return False


# ── EVALUADORES ───────────────────────────────────────────────────

def evaluate_budget_monthly(policy: AlertPolicy):
    accounts = _get_accounts(policy)
    total = sum(_monthly_cost(a) for a in accounts)
    threshold = policy.threshold or 0
    t_type = policy.threshold_type or "USD"

    reference = 0.0
    if t_type == "%" and accounts:
        try:
            months = CostExplorerService(accounts[0]).get_last_6_months_cost()
            past = [m["amount"] for m in months[:-1][-3:] if m["amount"] > 0]
            reference = sum(past) / len(past) if past else 0
        except Exception:
            pass

    fired = _exceeds(total, threshold, t_type, reference)
    return fired, {
        "costo_actual_mes": f"USD {round(total, 2)}",
        "umbral": f"{threshold} {t_type}",
        "periodo": "Mensual",
    }


def evaluate_budget_annual(policy: AlertPolicy):
    accounts = _get_accounts(policy)
    total = sum(_annual_cost(a) for a in accounts)
    threshold = policy.threshold or 0
    t_type = policy.threshold_type or "USD"

    fired = _exceeds(total, threshold, t_type)
    return fired, {
        "costo_acumulado_año": f"USD {round(total, 2)}",
        "umbral": f"{threshold} {t_type}",
        "periodo": "Anual",
    }


def evaluate_anomaly_spike(policy: AlertPolicy):
    accounts = _get_accounts(policy)
    if not accounts:
        return False, {}
    try:
        months = CostExplorerService(accounts[0]).get_last_6_months_cost()
        if len(months) < 2:
            return False, {}
        current = months[-1]["amount"]
        previous = months[-2]["amount"]
        if previous <= 0:
            return False, {}
        increase_pct = ((current - previous) / previous) * 100
        threshold = policy.threshold or 20
        fired = increase_pct >= threshold
        return fired, {
            "costo_mes_actual": f"USD {round(current, 2)}",
            "costo_mes_anterior": f"USD {round(previous, 2)}",
            "incremento": f"{round(increase_pct, 1)}%",
            "umbral_alerta": f"{threshold}% de incremento",
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
    q = AWSResourceInventory.query.filter_by(
        client_id=policy.client_id, is_active=True
    )
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
    q = AWSFinding.query.filter_by(
        client_id=policy.client_id, resolved=False
    )
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
        fired = _exceeds(projected, threshold, t_type)
        return fired, {
            "proyeccion_fin_de_mes": f"USD {round(projected, 2)}",
            "gasto_actual": f"USD {round(current_cost, 2)}",
            "dias_transcurridos": days_elapsed,
            "umbral": f"{threshold} {t_type}",
        }
    except Exception:
        return False, {}


def evaluate_off_hours(policy: AlertPolicy):
    tz = ZoneInfo("America/Santiago")
    hour = datetime.now(tz).hour
    is_off = hour >= 22 or hour < 8
    if not is_off:
        return False, {"razon": "Dentro de horario hábil (08:00–22:00 CL)"}
    q = AWSResourceInventory.query.filter_by(
        client_id=policy.client_id, is_active=True
    )
    if policy.aws_account_id:
        q = q.filter_by(aws_account_id=policy.aws_account_id)
    running = q.filter(
        AWSResourceInventory.state.in_(["running", "available"])
    ).all()
    threshold = int(policy.threshold or 1)
    fired = len(running) >= threshold
    return fired, {
        "recursos_activos_fuera_horario": len(running),
        "hora_actual_cl": f"{hour:02d}:00",
        "umbral": threshold,
    }


def evaluate_lifecycle(policy: AlertPolicy):
    lifecycle_types = ["snapshot", "lifecycle", "stale", "orphan", "unattached", "old_"]
    q = AWSFinding.query.filter_by(
        client_id=policy.client_id, resolved=False
    )
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


# ── MAPA DE EVALUADORES ───────────────────────────────────────────

EVALUATORS = {
    "budget-monthly": evaluate_budget_monthly,
    "budget-annual":  evaluate_budget_annual,
    "anomaly-spike":  evaluate_anomaly_spike,
    "service-cost":   evaluate_service_cost,
    "tagging-policy": evaluate_tagging_policy,
    "idle-resources": evaluate_idle_resources,
    "forecast":       evaluate_forecast,
    "off-hours":      evaluate_off_hours,
    "lifecycle":      evaluate_lifecycle,
}


# ── RUNNER PRINCIPAL ──────────────────────────────────────────────

def run_alert_engine() -> dict:
    """
    Evalúa todas las políticas configuradas y dispara alertas
    cuando se cumplen las condiciones.
    Retorna resumen de ejecución.
    """
    policies = AlertPolicy.query.filter(
        AlertPolicy.threshold.isnot(None)
    ).all()

    fired_count = 0
    skipped_count = 0
    error_count = 0

    for policy in policies:
        if not _should_fire(policy):
            skipped_count += 1
            continue

        evaluator = EVALUATORS.get(policy.policy_id)
        if not evaluator:
            skipped_count += 1
            continue

        try:
            fired, context = evaluator(policy)
            if fired:
                dispatch_alert(policy, context)
                _mark_fired(policy)
                fired_count += 1
        except Exception as e:
            print(f"[AlertEngine] Error en política {policy.id} ({policy.policy_id}): {e}")
            error_count += 1

    return {
        "total_politicas": len(policies),
        "alertas_disparadas": fired_count,
        "omitidas": skipped_count,
        "errores": error_count,
    }

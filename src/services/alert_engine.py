"""
ALERT ENGINE
============
Runner principal del motor de alertas.
Evalúa todas las políticas activas y dispara notificaciones.
"""

from datetime import datetime

from src.models.alert_policy import AlertPolicy
from src.models.database import db
from src.services.alert_notifier import dispatch_alert
from src.services.alert_evaluators import (
    evaluate_budget_monthly,
    evaluate_budget_annual,
    evaluate_anomaly_spike,
    evaluate_service_cost,
    evaluate_tagging_policy,
    evaluate_idle_resources,
    evaluate_forecast,
    evaluate_off_hours,
    evaluate_lifecycle,
)


# ── COOLDOWN POR PERÍODO ──────────────────────────────────────────────────────

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


# ── MAPA DE EVALUADORES ───────────────────────────────────────────────────────

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


# ── RUNNER PRINCIPAL ──────────────────────────────────────────────────────────

def run_alert_engine() -> dict:
    """
    Evalúa todas las políticas configuradas y dispara alertas
    cuando se cumplen las condiciones.
    Retorna resumen de ejecución.
    """
    policies = AlertPolicy.query.all()

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
                delivered = dispatch_alert(policy, context)
                if delivered:
                    _mark_fired(policy)
                    fired_count += 1
                else:
                    print(
                        f"[AlertEngine] Alerta no enviada en política "
                        f"{policy.id} ({policy.policy_id})"
                    )
                    error_count += 1
        except Exception as e:
            print(f"[AlertEngine] Error en política {policy.id} ({policy.policy_id}): {e}")
            error_count += 1

    return {
        "total_politicas": len(policies),
        "alertas_disparadas": fired_count,
        "omitidas": skipped_count,
        "errores": error_count,
    }

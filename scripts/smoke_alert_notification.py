"""
SMOKE ALERT NOTIFICATION
========================

Prueba end-to-end de notificación de alertas sin depender de métricas AWS.

Qué hace:
1) Crea una política temporal "smoke-test-notification"
2) Usa un evaluador temporal que siempre retorna fired=True
3) Ejecuta el flujo de envío real (email/slack/teams)
4) Marca fired solo si el envío fue exitoso
5) Elimina la política temporal al finalizar (por defecto)

Uso:
  python scripts/smoke_alert_notification.py \
    --client-id 123 \
    --channel email \
    --target ops@finopslatam.com

  python scripts/smoke_alert_notification.py \
    --client-id 123 \
    --channel slack \
    --target https://hooks.slack.com/services/XXX/YYY/ZZZ
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from app import app
from src.models.database import db
from src.models.alert_policy import AlertPolicy
from src.services.alert_notifier import dispatch_alert
from src.services import alert_engine


SMOKE_POLICY_ID = "smoke-test-notification"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smoke test de notificación real de alertas."
    )
    parser.add_argument("--client-id", type=int, required=True, help="ID del cliente")
    parser.add_argument(
        "--channel",
        choices=["email", "slack", "teams"],
        required=True,
        help="Canal de notificación",
    )
    parser.add_argument(
        "--target",
        required=True,
        help=(
            "Destino de la notificación. "
            "Para email: dirección de correo. "
            "Para slack/teams: URL del webhook."
        ),
    )
    parser.add_argument(
        "--aws-account-id",
        type=int,
        default=None,
        help="ID de cuenta AWS opcional para asociar la política temporal",
    )
    parser.add_argument(
        "--keep-policy",
        action="store_true",
        help="No elimina la política temporal al finalizar",
    )
    return parser


def _smoke_evaluator(policy: AlertPolicy):
    now_utc = datetime.utcnow().isoformat(timespec="seconds")
    return True, {
        "tipo": "smoke-test",
        "mensaje": "Prueba controlada de envío de alerta",
        "policy_id": policy.policy_id,
        "timestamp_utc": now_utc,
    }


def main() -> int:
    args = _build_parser().parse_args()

    created_policy_id: int | None = None
    previous_evaluator = alert_engine.EVALUATORS.get(SMOKE_POLICY_ID)

    with app.app_context():
        policy = AlertPolicy(
            client_id=args.client_id,
            aws_account_id=args.aws_account_id,
            policy_id=SMOKE_POLICY_ID,
            title=f"Smoke Test Alert {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            channel=args.channel,
            email=args.target,
            threshold=1.0,
            threshold_type="USD",
            period="daily",
        )

        db.session.add(policy)
        db.session.commit()
        created_policy_id = policy.id

        print(f"[SMOKE] Política temporal creada: id={policy.id}")

        alert_engine.EVALUATORS[SMOKE_POLICY_ID] = _smoke_evaluator

        try:
            fired, context = _smoke_evaluator(policy)
            print(f"[SMOKE] Condición evaluada: fired={fired}")

            if not fired:
                print("[SMOKE] Evaluador no disparó alerta (inesperado)")
                return 2

            delivered = dispatch_alert(policy, context)
            print(f"[SMOKE] Envío notificación: delivered={delivered}")

            if delivered:
                alert_engine._mark_fired(policy)
                refreshed = AlertPolicy.query.get(policy.id)
                last_fired = refreshed.last_fired_at if refreshed else None
                print(f"[SMOKE] last_fired_at: {last_fired}")

                if not last_fired:
                    print("[SMOKE] ERROR: Envío exitoso sin last_fired_at")
                    return 3

                print("[SMOKE] OK: notificación enviada y política marcada como fired")
                return 0

            print("[SMOKE] ERROR: la notificación no fue entregada")
            return 4

        finally:
            if previous_evaluator is None:
                alert_engine.EVALUATORS.pop(SMOKE_POLICY_ID, None)
            else:
                alert_engine.EVALUATORS[SMOKE_POLICY_ID] = previous_evaluator

            if created_policy_id and not args.keep_policy:
                tmp = AlertPolicy.query.get(created_policy_id)
                if tmp:
                    db.session.delete(tmp)
                    db.session.commit()
                    print(f"[SMOKE] Política temporal eliminada: id={created_policy_id}")


if __name__ == "__main__":
    sys.exit(main())

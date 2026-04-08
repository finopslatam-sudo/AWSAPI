"""
ALERT NOTIFIER
==============

Dispatcher de notificaciones para el engine de alertas.

Canales soportados:
- email  → correo directo al destinatario
- slack  → Incoming Webhook (URL almacenada en campo email)
- teams  → Incoming Webhook (URL almacenada en campo email)

Nota sobre Slack/Teams:
El campo `email` de la política almacena la URL del webhook
cuando el canal es slack o teams.
"""

import requests

from src.services.email_service import send_email
from src.services.email_templates import build_alert_fired_email


def dispatch_alert(policy, context: dict):
    """Dispara la alerta por el canal configurado en la política.

    Retorna:
        True  -> notificación enviada correctamente
        False -> no se envió o falló el canal
    """
    if policy.channel == "email":
        return _send_email_alert(policy, context)
    if policy.channel == "slack":
        return _send_slack_alert(policy, context)
    if policy.channel == "teams":
        return _send_teams_alert(policy, context)
    print(f"[AlertNotifier] Canal no soportado (política {policy.id}): {policy.channel}")
    return False


def _context_as_text(context: dict) -> str:
    lines = []
    for key, value in context.items():
        label = key.replace("_", " ").capitalize()
        if isinstance(value, list):
            lines.append(f"• {label}:")
            for item in value:
                lines.append(f"    - {item}")
        else:
            lines.append(f"• {label}: {value}")
    return "\n".join(lines)


# ── EMAIL ─────────────────────────────────────────────────────────

def _send_email_alert(policy, context: dict):
    if not policy.email:
        print(f"[AlertNotifier] Política {policy.id} sin email destino")
        return False

    body = build_alert_fired_email(
        policy_title=policy.title,
        policy_id=policy.policy_id,
        context=context,
    )

    return send_email(
        to=policy.email,
        subject=f"FinOpsLatam — Alerta: {policy.title}",
        body=body,
    )


# ── SLACK ─────────────────────────────────────────────────────────

def _send_slack_alert(policy, context: dict):
    webhook_url = policy.email
    if not webhook_url:
        print(f"[AlertNotifier] Política {policy.id} sin webhook Slack")
        return False

    context_text = _context_as_text(context)
    payload = {
        "text": (
            f":rotating_light: *Alerta FinOpsLatam — {policy.title}*\n\n"
            f"{context_text}\n\n"
            f"Revisa tu dashboard: https://www.finopslatam.com/dashboard/alertas"
        )
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if 200 <= response.status_code < 300:
            return True
        print(
            f"[AlertNotifier] Slack webhook HTTP {response.status_code} "
            f"(política {policy.id})"
        )
        return False
    except Exception as e:
        print(f"[AlertNotifier] Slack webhook error (política {policy.id}): {e}")
        return False


# ── TEAMS ─────────────────────────────────────────────────────────

def _send_teams_alert(policy, context: dict):
    webhook_url = policy.email
    if not webhook_url:
        print(f"[AlertNotifier] Política {policy.id} sin webhook Teams")
        return False

    context_text = _context_as_text(context)
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": f"Alerta: {policy.title}",
        "themeColor": "FF4444",
        "title": f"🚨 Alerta FinOpsLatam — {policy.title}",
        "text": context_text,
        "potentialAction": [{
            "@type": "OpenUri",
            "name": "Ver en Dashboard",
            "targets": [{"os": "default", "uri": "https://www.finopslatam.com/dashboard/alertas"}]
        }]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if 200 <= response.status_code < 300:
            return True
        print(
            f"[AlertNotifier] Teams webhook HTTP {response.status_code} "
            f"(política {policy.id})"
        )
        return False
    except Exception as e:
        print(f"[AlertNotifier] Teams webhook error (política {policy.id}): {e}")
        return False

"""Plantillas de correo para alertas del motor de alertas."""

BASE_URL = "https://www.finopslatam.com"


def build_alert_fired_email(policy_title: str, policy_id: str, context: dict) -> str:
    context_lines = []
    for key, value in context.items():
        label = key.replace("_", " ").capitalize()
        if isinstance(value, list):
            context_lines.append(f"  • {label}:")
            for item in value:
                context_lines.append(f"      - {item}")
        else:
            context_lines.append(f"  • {label}: {value}")
    context_text = "\n".join(context_lines)

    return f"""
🚨 ALERTA FINOPS — {policy_title.upper()}

Se ha cumplido la condición configurada en tu política:
"{policy_title}" (ID: {policy_id})

━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detalle de la alerta:

{context_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Accede a tu dashboard para revisar y tomar acción:
{BASE_URL}/dashboard/alertas

---
Este correo fue generado automáticamente por FinOpsLatam.
Para dejar de recibir esta alerta, elimina o edita la política
en la sección Políticas & Alertas de tu dashboard.

Saludos,
Equipo FinOpsLatam
"""

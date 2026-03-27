"""Plantillas de correo para solicitudes de upgrade de plan."""

BASE_URL = "https://www.finopslatam.com"
SUPPORT_EMAIL = "soporte@finopslatam.com"


def build_plan_changed_email(name: str, old_plan_name: str, new_plan_name: str) -> str:
    return f"""
Hola {name or "Usuario"},

Te informamos que tu plan en FinOpsLatam ha sido actualizado. 🎉

🚀 Cambio de plan:
Anterior: {old_plan_name}
Nuevo: {new_plan_name}

Los cambios se aplican de inmediato.

Accede aquí:
{BASE_URL}

Saludos,
Equipo FinOpsLatam
"""


def build_plan_upgrade_request_received_email(
    name: str,
    client_id: int,
    email: str,
    old_plan_name: str,
    new_plan_name: str,
) -> str:
    return f"""
Hola {name or "Usuario"},

Hemos recibido correctamente tu solicitud de cambio de plan en FinOpsLatam.

Cliente ID: {client_id}
Usuario: {email}

🚀 Plan actual: {old_plan_name}
🚀 Plan solicitado: {new_plan_name}

Tu solicitud será revisada por un administrador.
Te notificaremos cuando el cambio sea aprobado o rechazado.

Puedes seguir accediendo normalmente a la plataforma.

{BASE_URL}

Saludos,
Equipo FinOpsLatam
"""


def build_plan_upgrade_rejected_email(name: str, plan_name: str) -> str:
    return f"""
Hola {name or "Usuario"},

Tu solicitud de upgrade al plan:

{plan_name}

no ha sido aprobada por el administrador.

Si necesitas más información puedes escribir a:

{SUPPORT_EMAIL}

Saludos,
Equipo FinOpsLatam
"""


def build_internal_plan_upgrade_alert(
    name: str,
    client_id: int,
    email: str,
    old_plan: str,
    new_plan_name: str,
) -> str:
    return f"""
Nueva solicitud de upgrade de plan en FinOpsLatam.

Cliente ID: {client_id}
Usuario: {email}
Nombre: {name or "Usuario"}

Plan actual: {old_plan}
Plan solicitado: {new_plan_name}

Estado: PENDING

Un administrador debe revisar esta solicitud.

Panel admin:
https://www.finopslatam.com/dashboard/admin/upgrades

Saludos,
FinOpsLatam System
"""

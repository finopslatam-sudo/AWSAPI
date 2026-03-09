"""
EMAIL TEMPLATES
===============

Plantillas de correos transaccionales del sistema.

IMPORTANTE:
- Este archivo SOLO construye texto
- NO envía correos
- NO contiene lógica de negocio
- NO accede a base de datos
"""

from datetime import datetime
from zoneinfo import ZoneInfo

BASE_URL = "https://www.finopslatam.com"
SUPPORT_EMAIL = "soporte@finopslatam.com"


# ================================
# RECUPERACIÓN DE PASSWORD
# ================================
def build_forgot_password_email(
    name: str,
    email: str,
    temp_password: str
) -> str:
    return f"""
Hola {name or "Usuario"} ,

Se solicitó la recuperación de acceso a tu cuenta FinOpsLatam.

Usuario: {email}
Contraseña temporal: {temp_password}

Esta contraseña expira en 30 minutos.

Accede aquí:
{BASE_URL}

Saludos,
Equipo FinOpsLatam
"""


# ================================
# CUENTA DESACTIVADA
# ================================
def build_account_deactivated_email(name: str) -> str:
    return f"""
Hola {name or "Usuario"},

Tu cuenta en FinOpsLatam ha sido desactivada temporalmente 🔒

Si crees que esto es un error o necesitas más información,
puedes contactarnos en:

{SUPPORT_EMAIL}

Saludos,
Equipo FinOpsLatam
"""


# ================================
# CUENTA REACTIVADA
# ================================
def build_account_reactivated_email(name: str) -> str:
    return f"""
Hola {name or "Usuario"},

Tu cuenta en FinOpsLatam ha sido reactivada exitosamente 🎉

Por seguridad, en tu próximo inicio de sesión se te pedirá
actualizar tu contraseña.

Si tienes dudas, escríbenos a:
{SUPPORT_EMAIL}

Saludos,
Equipo FinOpsLatam
"""


# ================================
# PASSWORD CAMBIADO
# ================================
def build_password_changed_email(name: str) -> str:
    return f"""
Hola {name or "Usuario"},

Te confirmamos que tu contraseña fue cambiada correctamente. 🎉

Si no realizaste este cambio, contáctanos de inmediato:
{SUPPORT_EMAIL}

Saludos,
Equipo FinOpsLatam
"""


# ================================
# RESET PASSWORD POR ADMIN
# ================================
def build_admin_reset_password_email(
    name: str,
    email: str,
    password: str
) -> str:
    return f"""
Hola {name or "Usuario"},

Un administrador ha restablecido la contraseña de tu cuenta.

🔐 Datos de acceso
Usuario: {email}
Contraseña temporal: {password}

Debes cambiarla al iniciar sesión.

👉 {BASE_URL}

Saludos,
Equipo FinOpsLatam
"""


# ================================
# ALERTA LOGIN ROOT
# ================================
def build_root_login_alert_email(
    name: str,
    email: str,
    ip_address: str
) -> str:
    now_cl = datetime.now(ZoneInfo("America/Santiago"))
    return f"""
⚠️ ALERTA DE SEGURIDAD — FinOpsLatam

Se ha iniciado sesión con la cuenta ROOT.

Usuario: {email}
Nombre: {name or "ROOT"}
IP: {ip_address}
Fecha: {now_cl.strftime("%d-%m-%Y")}
Hora: {now_cl.strftime("%H:%M:%S")}


Si no reconoces este acceso,
contacta inmediatamente a {SUPPORT_EMAIL}
"""

# ================================
# CAMBIO DE PLAN
# ================================
def build_plan_changed_email(
    name: str,
    old_plan_name: str,
    new_plan_name: str
) -> str:
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
# ================================
# BIENVENIDA USUARIO CREADO POR ADMIN
# ================================
def build_user_welcome_email(
    name: str,
    email: str,
    password: str
) -> str:
    return f"""
Hola {name or "Usuario"},

Tu cuenta en FinOpsLatam ha sido creada exitosamente 🎉

🔐 Datos de acceso:
Usuario: {email}
Contraseña: {password}

Por seguridad, deberás cambiar tu contraseña
en el primer inicio de sesión.

Accede aquí:
{BASE_URL}

Saludos,
Equipo FinOpsLatam
"""
# ================================
# UPGRADE de plan
# ================================
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

# ================================
# PLAN UPGRADE REJECTED
# ================================
def build_plan_upgrade_rejected_email(
    name: str,
    plan_name: str
) -> str:

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
# ================================
# ALERTA INTERNA UPGRADE PLAN
# ================================
def build_internal_plan_upgrade_alert(
    name: str,
    client_id: int,
    email: str,
    old_plan: str,
    new_plan_name: str
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
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

Te confirmamos que tu contraseña fue cambiada correctamente.

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
now_cl = datetime.now(ZoneInfo("America/Santiago"))
Fecha: {now_cl.strftime("%Y-%m-%d %H:%M:%S %Z")}


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

Te informamos que tu plan en FinOpsLatam ha sido actualizado.

📦 Cambio de plan:
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

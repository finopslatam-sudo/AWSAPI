from datetime import datetime

# ================================
# EMAIL RECUPERACION DE PASSWORD
# ================================
def build_forgot_password_email(name, email, temp_password):
    return f"""
Hola {name},

Se solicitó la recuperación de acceso a tu cuenta FinOpsLatam.

Usuario: {email}
Contraseña temporal: {temp_password}

Esta contraseña expira en 30 minutos.

Accede aquí:
https://www.finopslatam.com

Saludos,
Equipo FinOpsLatam
"""

# ================================
# EMAIL HELPERS CUENTA DESACTIVADA
# ================================
def build_account_deactivated_email(nombre):
    return f"""
Hola {nombre},

Tu cuenta en FinOpsLatam ha sido desactivada temporalmente 🔒

Si crees que esto es un error o necesitas más información,
puedes contactarnos en:

soporte@finopslatam.com

Saludos,
Equipo FinOpsLatam
"""

# ================================
# EMAIL HELPERS CUENTA ACTIVADA
# ================================
def build_account_reactivated_email(nombre):
    return f"""
Hola {nombre},

Tu cuenta en FinOpsLatam ha sido reactivada exitosamente 🎉

Por seguridad, en tu próximo inicio de sesión se te pedirá
actualizar tu contraseña.

👉 Accede aquí:
https://www.finopslatam.com/

Si tienes dudas, escríbenos a:
soporte@finopslatam.com

Saludos,
Equipo FinOpsLatam
"""
# ================================
# EMAIL PASSWORD CHANGE
# ================================
def build_password_changed_email(nombre: str) -> str:
    return f"""
Hola {nombre},

Te confirmamos que tu contraseña fue cambiada correctamente.

Si no realizaste este cambio, contáctanos de inmediato:
soporte@finopslatam.com

Saludos,
Equipo FinOpsLatam
"""

# ================================
# EMAIL REESET PASSWORD FOR ADMIN 
# ================================

def build_admin_reset_password_email(
    nombre: str,
    email: str,
    password: str
) -> str:
    return f"""
Hola {nombre},

Un administrador ha restablecido la contraseña de tu cuenta.

🔐 Datos de acceso
Usuario: {email}
Contraseña temporal: {password}

Debes cambiarla al iniciar sesión.

👉 https://www.finopslatam.com/

Saludos,
Equipo FinOpsLatam
"""
# ================================
# EMAIL INICIO SESION NO AUTORIZADO 
# ================================
def build_root_login_alert_email(nombre, email, ip_address):
    return f"""
⚠️ ALERTA DE SEGURIDAD — FinOpsLatam

Se ha iniciado sesión con la cuenta ROOT.

Usuario: {email}
Nombre: {nombre}
IP: {ip_address}
Fecha: {datetime.utcnow().isoformat()} UTC

Si no reconoces este acceso,
contacta inmediatamente a soporte@finopslatam.com
"""
# ================================
# EMAIL CAMBIO DE PLAN 
# ================================
def build_plan_changed_email(nombre: str, plan_name: str) -> str:
    return f"""
Hola {nombre},

Te informamos que tu plan en FinOpsLatam ha sido actualizado.

📦 Nuevo plan:
{plan_name}

Los cambios se aplican de inmediato.

Accede aquí:
https://www.finopslatam.com/

Saludos,
Equipo FinOpsLatam
"""

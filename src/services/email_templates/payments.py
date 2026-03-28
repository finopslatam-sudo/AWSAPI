"""
Email templates — PayPal payments
===================================
Correos transaccionales para el flujo de pago con PayPal.
"""


def build_payment_welcome_email(nombre: str, plan_name: str) -> str:
    """
    Correo al cliente tras confirmar el pago.
    Informa que su cuenta será activada manualmente por un administrador.
    """
    return f"""Hola {nombre},

¡Gracias por elegir FinOps Latam!

Hemos recibido tu pago correctamente para el plan:

  → {plan_name}

En unos minutos un administrador validará tu cuenta y recibirás tus
credenciales de acceso por correo electrónico.

Si tienes alguna consulta, no dudes en contactarnos respondiendo este correo.

Bienvenido a FinOps Latam.
El equipo de FinOps Latam
https://www.finopslatam.com
"""


def build_admin_new_payment_email(
    nombre: str,
    empresa: str,
    email: str,
    pais: str,
    plan_name: str,
    subscription_id: str,
) -> str:
    """
    Correo a administradores cuando un cliente completa el pago.
    Indica que deben crear el usuario y enviar credenciales manualmente.
    """
    return f"""Nuevo cliente ha contratado un plan en FinOps Latam.

DATOS DEL CLIENTE
-----------------
Nombre         : {nombre}
Empresa        : {empresa}
Email          : {email}
País           : {pais}
Plan           : {plan_name}
Suscripción    : {subscription_id}

ACCIÓN REQUERIDA
----------------
1. Crear usuario en el sistema para: {email}
2. Asignar el plan: {plan_name}
3. Enviar credenciales de acceso al cliente

Este cliente NO tiene acceso aún. La activación es manual.

-- Sistema FinOps Latam --
"""

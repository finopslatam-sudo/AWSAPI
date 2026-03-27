"""
STRIPE SERVICE
==============
Lógica de integración con Stripe.

Responsabilidades:
- Crear sesiones de checkout (suscripción mensual)
- Mapear plan_code → Stripe price_id desde ENV

Variables de entorno requeridas:
  STRIPE_SECRET_KEY       — clave secreta de Stripe
  STRIPE_PRICE_FOUNDATION
  STRIPE_PRICE_PROFESSIONAL
  STRIPE_PRICE_ENTERPRISE
  STRIPE_PRICE_CONSULTORIA
  FRONTEND_URL            — base URL del frontend (para success/cancel URLs)
"""

import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# Mapa plan_code → variable de entorno con el price_id de Stripe
_PRICE_ENV: dict[str, str] = {
    "foundation":   "STRIPE_PRICE_FOUNDATION",
    "professional": "STRIPE_PRICE_PROFESSIONAL",
    "enterprise":   "STRIPE_PRICE_ENTERPRISE",
    "consultoria":  "STRIPE_PRICE_CONSULTORIA",
}

PLAN_NAMES: dict[str, str] = {
    "foundation":   "FinOps Foundation",
    "professional": "FinOps Professional",
    "enterprise":   "FinOps Enterprise",
    "consultoria":  "Consultoría FinOps Estratégica",
}


def get_price_id(plan_code: str) -> str | None:
    """Retorna el Stripe price_id para el plan dado, o None si no está configurado."""
    env_var = _PRICE_ENV.get(plan_code)
    if not env_var:
        return None
    return os.getenv(env_var) or None


def create_checkout_session(
    plan_code: str,
    email: str,
    nombre: str = "",
    empresa: str = "",
    pais: str = "",
    telefono: str = "",
) -> str:
    """
    Crea una sesión de checkout de Stripe tipo 'subscription'.

    Retorna la URL de checkout.
    Lanza ValueError si el plan no es válido o el price_id no está configurado.
    Lanza stripe.error.StripeError en caso de error con la API de Stripe.
    """
    price_id = get_price_id(plan_code)
    if not price_id:
        raise ValueError(f"price_id no configurado para plan '{plan_code}'")

    frontend_url = os.getenv("FRONTEND_URL", "https://www.finopslatam.com").rstrip("/")
    plan_name    = PLAN_NAMES.get(plan_code, plan_code)

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=email,
        line_items=[{"price": price_id, "quantity": 1}],
        metadata={
            "plan_code": plan_code,
            "plan_name": plan_name,
            "nombre":    nombre,
            "empresa":   empresa,
            "pais":      pais,
            "telefono":  telefono,
        },
        success_url=f"{frontend_url}/pago/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{frontend_url}/pago/cancel?plan={plan_code}",
        allow_promotion_codes=True,
    )

    return session.url

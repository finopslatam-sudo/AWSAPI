"""
STRIPE SERVICE
==============
Integración con Stripe API para suscripciones recurrentes con tarjeta embebida.

Flujo:
  1. create_customer()      — crea el Customer en Stripe
  2. create_subscription()  — crea la suscripción incompleta, retorna client_secret
  3. Frontend confirma el pago con stripe.confirmPayment(client_secret)
  4. Stripe cobra y activa la suscripción automáticamente cada mes

Variables de entorno requeridas:
  STRIPE_SECRET_KEY
  STRIPE_WEBHOOK_SECRET
  STRIPE_PRICE_FOUNDATION
  STRIPE_PRICE_PROFESSIONAL
  STRIPE_PRICE_ENTERPRISE
  STRIPE_PRICE_CONSULTORIA
"""

import os
import stripe as stripe_lib

PLAN_NAMES: dict[str, str] = {
    "foundation":   "FinOps Foundation",
    "professional": "FinOps Professional",
    "enterprise":   "FinOps Enterprise",
    "consultoria":  "Consultoría FinOps Estratégica",
}

_PRICE_ENV: dict[str, str] = {
    "foundation":   "STRIPE_PRICE_FOUNDATION",
    "professional": "STRIPE_PRICE_PROFESSIONAL",
    "enterprise":   "STRIPE_PRICE_ENTERPRISE",
    "consultoria":  "STRIPE_PRICE_CONSULTORIA",
}


def _stripe() -> stripe_lib:
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        raise ValueError("STRIPE_SECRET_KEY no configurada")
    stripe_lib.api_key = key
    return stripe_lib


def get_price_id(plan_code: str) -> str | None:
    """Retorna el Stripe Price ID para el plan dado, o None si no está configurado."""
    env_var = _PRICE_ENV.get(plan_code)
    if not env_var:
        return None
    return os.getenv(env_var) or None


def create_customer(email: str, nombre: str = "", empresa: str = "") -> str:
    """Crea un Customer en Stripe y retorna su ID."""
    s = _stripe()
    customer = s.Customer.create(
        email=email,
        name=nombre or email,
        metadata={"empresa": empresa},
    )
    return customer["id"]


def create_subscription(
    customer_id: str,
    plan_code: str,
    metadata: dict | None = None,
) -> tuple[str, str]:
    """
    Crea una suscripción incompleta en Stripe.
    El frontend debe confirmar el pago con el client_secret retornado.

    Retorna (subscription_id, client_secret).
    Lanza ValueError si el price_id no está configurado.
    """
    s = _stripe()
    price_id = get_price_id(plan_code)
    if not price_id:
        raise ValueError(f"STRIPE price_id no configurado para '{plan_code}'")

    subscription = s.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        payment_behavior="default_incomplete",
        payment_settings={"save_default_payment_method": "on_subscription"},
        expand=["latest_invoice.payment_intent"],
        metadata=metadata or {},
    )

    client_secret = subscription["latest_invoice"]["payment_intent"]["client_secret"]
    return subscription["id"], client_secret


def construct_webhook_event(payload: bytes, sig_header: str) -> dict:
    """Verifica y parsea un evento de webhook Stripe. Lanza excepción si la firma es inválida."""
    s = _stripe()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise ValueError("STRIPE_WEBHOOK_SECRET no configurada")
    return s.Webhook.construct_event(payload, sig_header, webhook_secret)

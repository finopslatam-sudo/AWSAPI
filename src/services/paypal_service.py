"""
PAYPAL SERVICE
==============
Integración con PayPal Subscriptions API v1.

Variables de entorno requeridas:
  PAYPAL_CLIENT_ID
  PAYPAL_CLIENT_SECRET
  PAYPAL_PLAN_FOUNDATION
  PAYPAL_PLAN_PROFESSIONAL
  PAYPAL_PLAN_ENTERPRISE
  PAYPAL_PLAN_CONSULTORIA
  PAYPAL_ENV      — 'sandbox' | 'production' (default: production)
  PAYPAL_WEBHOOK_ID — ID del webhook registrado en PayPal Dashboard
  FRONTEND_URL    — base URL del frontend (para return/cancel URLs)
"""

import os
import json
import requests

PLAN_NAMES: dict[str, str] = {
    "foundation":   "FinOps Foundation",
    "professional": "FinOps Professional",
    "enterprise":   "FinOps Enterprise",
    "consultoria":  "Consultoría FinOps Estratégica",
}

_PLAN_ENV: dict[str, str] = {
    "foundation":   "PAYPAL_PLAN_FOUNDATION",
    "professional": "PAYPAL_PLAN_PROFESSIONAL",
    "enterprise":   "PAYPAL_PLAN_ENTERPRISE",
    "consultoria":  "PAYPAL_PLAN_CONSULTORIA",
}


def _base_url() -> str:
    env = os.getenv("PAYPAL_ENV", "production").lower()
    if env == "sandbox":
        return "https://api-m.sandbox.paypal.com"
    return "https://api-m.paypal.com"


def get_access_token() -> str:
    """Obtiene un access token de PayPal via OAuth2."""
    client_id = os.getenv("PAYPAL_CLIENT_ID", "")
    secret    = os.getenv("PAYPAL_CLIENT_SECRET", "")
    if not client_id or not secret:
        raise ValueError("PAYPAL_CLIENT_ID y PAYPAL_CLIENT_SECRET son requeridos")

    resp = requests.post(
        f"{_base_url()}/v1/oauth2/token",
        auth=(client_id, secret),
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_plan_id(plan_code: str) -> str | None:
    """Retorna el PayPal Plan ID para el plan dado, o None si no está configurado."""
    env_var = _PLAN_ENV.get(plan_code)
    if not env_var:
        return None
    return os.getenv(env_var) or None


def create_subscription(
    plan_code: str,
    email: str,
    nombre: str = "",
    empresa: str = "",
    pais: str = "",
    telefono: str = "",
) -> tuple[str, str]:
    """
    Crea una suscripción en PayPal.

    Retorna (subscription_id, approval_url).
    Lanza ValueError si el plan no es válido o no está configurado.
    Lanza requests.HTTPError en caso de error con la API de PayPal.
    """
    plan_id = get_plan_id(plan_code)
    if not plan_id:
        raise ValueError(f"PayPal plan_id no configurado para '{plan_code}'")

    plan_name    = PLAN_NAMES.get(plan_code, plan_code)
    frontend_url = os.getenv("FRONTEND_URL", "https://www.finopslatam.com").rstrip("/")

    parts      = nombre.strip().split(" ", 1)
    given_name = parts[0][:50]
    surname    = (parts[1] if len(parts) > 1 else ".")[:50]

    token = get_access_token()

    payload = {
        "plan_id":    plan_id,
        "custom_id":  plan_code,
        "subscriber": {
            "email_address": email,
            "name": {"given_name": given_name, "surname": surname},
        },
        "application_context": {
            "brand_name":  "FinOps Latam",
            "locale":      "es-MX",
            "user_action": "SUBSCRIBE_NOW",
            "return_url":  f"{frontend_url}/pago/success?plan={plan_code}",
            "cancel_url":  f"{frontend_url}/pago/cancel?plan={plan_code}",
        },
    }

    resp = requests.post(
        f"{_base_url()}/v1/billing/subscriptions",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        timeout=20,
    )
    resp.raise_for_status()

    data            = resp.json()
    subscription_id = data.get("id", "")

    for link in data.get("links", []):
        if link.get("rel") == "approve":
            return subscription_id, link["href"]

    raise ValueError("PayPal no retornó URL de aprobación")


def verify_webhook_signature(headers, body: bytes) -> bool:
    """
    Verifica la firma de un webhook de PayPal usando la API de verificación.
    Retorna True si la firma es válida.
    """
    webhook_id = os.getenv("PAYPAL_WEBHOOK_ID", "")
    if not webhook_id:
        return False

    try:
        token = get_access_token()
        verification_payload = {
            "auth_algo":         headers.get("PAYPAL-AUTH-ALGO", ""),
            "cert_url":          headers.get("PAYPAL-CERT-URL", ""),
            "transmission_id":   headers.get("PAYPAL-TRANSMISSION-ID", ""),
            "transmission_sig":  headers.get("PAYPAL-TRANSMISSION-SIG", ""),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME", ""),
            "webhook_id":        webhook_id,
            "webhook_event":     json.loads(body),
        }
        resp = requests.post(
            f"{_base_url()}/v1/notifications/verify-webhook-signature",
            json=verification_payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            timeout=15,
        )
        return resp.status_code == 200 and resp.json().get("verification_status") == "SUCCESS"
    except Exception:
        return False

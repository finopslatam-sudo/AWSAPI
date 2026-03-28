"""
MERCADO PAGO SERVICE
====================
Integración con Mercado Pago Subscriptions API (preapproval).

Variables de entorno requeridas:
  MP_ACCESS_TOKEN    — token de acceso (producción o sandbox)
  MP_CURRENCY        — moneda: 'USD', 'CLP', 'ARS', etc. (default: USD)
  FRONTEND_URL       — URL base del frontend
  API_URL            — URL base del backend (para el notification_url)

Flujo:
  1. create_subscription()      — crea preapproval en MP, retorna (id, init_point)
  2. Frontend redirige al usuario a init_point
  3. MP notifica al webhook con el preapproval_id
  4. get_subscription_status()  — consulta MP para validar estado real

SEGURIDAD:
  - Nunca activar basándose solo en el webhook
  - Siempre verificar el estado con get_subscription_status() antes de activar
"""

import os
import mercadopago


PLAN_NAMES: dict[str, str] = {
    "foundation":   "FinOps Foundation",
    "professional": "FinOps Professional",
    "enterprise":   "FinOps Enterprise",
    "consultoria":  "Consultoría FinOps Estratégica",
}

PLAN_AMOUNTS: dict[str, float] = {
    "foundation":   950.0,
    "professional": 1750.0,
    "enterprise":   2550.0,
    "consultoria":  2550.0,
}


def _sdk() -> mercadopago.SDK:
    """Retorna instancia del SDK autenticada. Lanza ValueError si falta el token."""
    token = os.getenv("MP_ACCESS_TOKEN", "")
    if not token:
        raise ValueError("MP_ACCESS_TOKEN no configurada")
    return mercadopago.SDK(token)


def create_subscription(
    plan_code: str,
    user_email: str,
    nombre: str = "",
    empresa: str = "",
    pais: str = "",
) -> tuple[str, str]:
    """
    Crea una suscripción mensual en Mercado Pago (preapproval).

    Retorna (preapproval_id, init_point).
    Lanza ValueError si el plan no es válido o hay error en MP.
    """
    plan_name = PLAN_NAMES.get(plan_code)
    amount    = PLAN_AMOUNTS.get(plan_code)
    if not plan_name or amount is None:
        raise ValueError(f"Plan inválido: '{plan_code}'")

    currency      = os.getenv("MP_CURRENCY", "USD")
    frontend_url  = os.getenv("FRONTEND_URL", "https://www.finopslatam.com").rstrip("/")
    backend_url   = os.getenv("API_URL",      "https://api.finopslatam.com").rstrip("/")

    sdk = _sdk()

    preapproval_data = {
        "reason": plan_name,
        "auto_recurring": {
            "frequency":          1,
            "frequency_type":     "months",
            "transaction_amount": amount,
            "currency_id":        currency,
        },
        "payer_email":       user_email,
        "back_url":          f"{frontend_url}/pago/success?plan={plan_code}",
        "status":            "pending",
        "notification_url":  f"{backend_url}/api/webhooks/mercadopago",
    }

    result = sdk.preapproval().create(preapproval_data)

    if result["status"] not in (200, 201):
        error_detail = result.get("response", {})
        raise ValueError(f"Error Mercado Pago al crear suscripción: {error_detail}")

    response       = result["response"]
    preapproval_id = response.get("id", "")
    init_point     = response.get("init_point", "")

    if not preapproval_id or not init_point:
        raise ValueError("Mercado Pago no retornó id o init_point válidos")

    return preapproval_id, init_point


def get_subscription_status(preapproval_id: str) -> str:
    """
    Consulta el estado real de una suscripción directamente en la API de Mercado Pago.

    NUNCA confiar en el cuerpo del webhook — siempre llamar esta función
    para verificar el estado antes de activar una suscripción.

    Posibles estados: 'authorized', 'pending', 'paused', 'cancelled'.
    Lanza ValueError si la consulta falla.
    """
    sdk    = _sdk()
    result = sdk.preapproval().get(preapproval_id)

    if result["status"] != 200:
        raise ValueError(
            f"Error consultando preapproval '{preapproval_id}': "
            f"HTTP {result['status']}"
        )

    return result["response"].get("status", "")

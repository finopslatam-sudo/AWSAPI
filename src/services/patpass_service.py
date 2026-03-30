"""
PATPASS SERVICE
===============
Integración con PatPass Comercio (Transbank) para suscripciones mensuales.

Variables de entorno requeridas:
  PATPASS_ENV            — 'integration' | 'production' (default: integration)
  PATPASS_COMMERCE_CODE  — código de comercio productivo
  PATPASS_API_KEY        — llave secreta productiva
  PATPASS_AMOUNT_FOUNDATION    — monto mensual en CLP (Foundation)
  PATPASS_AMOUNT_PROFESSIONAL  — monto mensual en CLP (Professional)
  PATPASS_AMOUNT_ENTERPRISE    — monto mensual en CLP (Enterprise)
  FRONTEND_URL           — base URL del frontend

Credenciales de integración (pre-configuradas en SDK):
  Código de comercio: 28299257
  Api Key Secret:     cxxXQgGD9vrVe4M41FIt
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger("patpass")

PLAN_NAMES: dict[str, str] = {
    "foundation":   "FinOps Foundation",
    "professional": "FinOps Professional",
    "enterprise":   "FinOps Enterprise",
}

# Montos en CLP (configurables por env var)
_DEFAULT_AMOUNTS_CLP: dict[str, int] = {
    "foundation":   950,
    "professional": 1750,
    "enterprise":   2550,
}

_AMOUNT_ENV: dict[str, str] = {
    "foundation":   "PATPASS_AMOUNT_FOUNDATION",
    "professional": "PATPASS_AMOUNT_PROFESSIONAL",
    "enterprise":   "PATPASS_AMOUNT_ENTERPRISE",
}


def get_plan_amount(plan_code: str) -> int:
    env_var = _AMOUNT_ENV.get(plan_code)
    if env_var:
        val = os.getenv(env_var)
        if val and val.isdigit():
            return int(val)
    return _DEFAULT_AMOUNTS_CLP.get(plan_code, 1000)


def _is_production() -> bool:
    return os.getenv("PATPASS_ENV", "integration").lower() == "production"


def _get_inscription():
    """Retorna instancia de Inscription configurada según ambiente."""
    from transbank.patpass_comercio.inscription import Inscription
    if _is_production():
        from transbank.patpass_comercio.schema import PatpassOptions
        from transbank.common.integration_type import WebpayIntegrationType
        commerce_code = os.getenv("PATPASS_COMMERCE_CODE", "")
        api_key       = os.getenv("PATPASS_API_KEY", "")
        if not commerce_code or not api_key:
            raise ValueError("PATPASS_COMMERCE_CODE y PATPASS_API_KEY son requeridos en producción")
        return Inscription(PatpassOptions(commerce_code, api_key, WebpayIntegrationType.LIVE))
    return Inscription()  # credenciales de integración pre-configuradas en SDK


def create_inscription(
    plan_code: str,
    email: str,
    buy_order: str,
) -> tuple[str, str]:
    """
    Inicia una inscripción PatPass.
    Retorna (redirect_url, token).
    """
    frontend_url = os.getenv("FRONTEND_URL", "https://www.finopslatam.com").rstrip("/")
    redirect_url = f"{frontend_url}/pago/patpass-return"

    inscription = _get_inscription()
    response = inscription.start(
        buy_order=buy_order,
        email=email,
        redirect_url=redirect_url,
        username=email,
    )
    return response.url, response.token


def confirm_inscription(token_ws: str) -> dict:
    """
    Confirma la inscripción después del retorno de Transbank.
    Retorna dict con resultado.
    """
    inscription = _get_inscription()
    response = inscription.finish(token=token_ws)
    return {
        "is_inscribed":       getattr(response, "is_inscribed", False),
        "tbk_user":           getattr(response, "tbk_user", None),
        "authorization_code": getattr(response, "authorization_code", None),
        "card_type":          getattr(response, "card_type", None),
        "card_number":        getattr(response, "card_number", None),
    }


def charge_subscription(tbk_user: str, email: str, amount_clp: int, buy_order: str) -> dict:
    """
    Cobra una suscripción activa. Llamar mensualmente por cada inscripción activa.
    Retorna dict con resultado del cobro.
    """
    from transbank.patpass_comercio.transaction import Transaction

    if _is_production():
        from transbank.patpass_comercio.schema import PatpassOptions
        from transbank.common.integration_type import WebpayIntegrationType
        commerce_code = os.getenv("PATPASS_COMMERCE_CODE", "")
        api_key       = os.getenv("PATPASS_API_KEY", "")
        tx = Transaction(PatpassOptions(commerce_code, api_key, WebpayIntegrationType.LIVE))
    else:
        tx = Transaction()

    response = tx.authorize(
        buy_order=buy_order,
        tbk_user=tbk_user,
        email=email,
        amount=amount_clp,
    )
    return {
        "authorization_code": getattr(response, "authorization_code", None),
        "amount":             getattr(response, "amount", None),
        "response_code":      getattr(response, "response_code", None),
    }

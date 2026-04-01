"""
PATPASS SERVICE
===============
Integración con PatPass Comercio (Transbank) para suscripciones mensuales.

Variables de entorno requeridas:
  PATPASS_ENV            — 'integration' | 'production' (default: integration)
  PATPASS_COMMERCE_CODE  — código de comercio productivo
  PATPASS_API_KEY        — llave secreta productiva
  PATPASS_COMMERCE_EMAIL — email del comercio para Transbank
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

logger = logging.getLogger("patpass")

PLAN_NAMES: dict[str, str] = {
    "foundation":   "FinOps Foundation",
    "professional": "FinOps Professional",
    "enterprise":   "FinOps Enterprise",
}

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
    from transbank.common.options import PatpassComercioOptions
    from transbank.common.integration_type import IntegrationType

    if _is_production():
        commerce_code = os.getenv("PATPASS_COMMERCE_CODE", "")
        api_key       = os.getenv("PATPASS_API_KEY", "")
        if not commerce_code or not api_key:
            raise ValueError("PATPASS_COMMERCE_CODE y PATPASS_API_KEY son requeridos en producción")
        opts = PatpassComercioOptions(commerce_code, api_key, IntegrationType.LIVE)
    else:
        opts = PatpassComercioOptions("28299257", "cxxXQgGD9vrVe4M41FIt", IntegrationType.TEST)

    return Inscription(opts)


def _split_nombre(nombre: str) -> tuple[str, str, str]:
    """
    Separa nombre completo en (name, last_name, second_last_name).
    Ej: 'Juan Pérez García' → ('Juan', 'Pérez', 'García')
    """
    parts = nombre.strip().split()
    if len(parts) == 0:
        return ("Sin nombre", "", "")
    if len(parts) == 1:
        return (parts[0], parts[0], "")
    if len(parts) == 2:
        return (parts[0], parts[1], "")
    return (parts[0], parts[1], " ".join(parts[2:]))


def create_inscription(
    plan_name: str,
    nombre: str,
    email: str,
    rut: str,
    telefono: str,
    buy_order: str,
    amount_clp: int,
) -> tuple[str, str]:
    """
    Inicia una inscripción PatPass.
    Retorna (redirect_url, token).
    """
    frontend_url   = os.getenv("FRONTEND_URL", "https://www.finopslatam.com").rstrip("/")
    redirect_url   = f"{frontend_url}/pago/patpass-return"
    commerce_email = os.getenv("PATPASS_COMMERCE_EMAIL", "pagos@finopslatam.com")

    name, last_name, second_last_name = _split_nombre(nombre)
    cell_phone = (telefono or "").strip() or "000000000"

    inscription = _get_inscription()
    response = inscription.start(
        url=redirect_url,
        name=name,
        last_name=last_name,
        second_last_name=second_last_name,
        rut=rut,
        service_id=buy_order,
        final_url=redirect_url,
        max_amount=float(amount_clp),
        phone=cell_phone,
        cell_phone=cell_phone,
        patpass_name=plan_name,
        person_email=email,
        commerce_email=commerce_email,
        address="N/A",
        city="Chile",
    )
    if isinstance(response, int):
        logger.error("Transbank retornó body vacío con status %s", response)
        raise RuntimeError(f"Transbank respondió sin cuerpo (HTTP {response})")
    if not isinstance(response, dict) or "url" not in response or "token" not in response:
        logger.error("Respuesta inesperada de Transbank: %s", response)
        raise RuntimeError("Respuesta inesperada de Transbank")
    return response["url"], response["token"]


def confirm_inscription(token_ws: str) -> dict:
    """
    Confirma la inscripción después del retorno de Transbank.
    Retorna dict con resultado.
    """
    inscription = _get_inscription()
    response    = inscription.status(token=token_ws)
    if isinstance(response, int):
        logger.error("Transbank status retornó body vacío con status %s", response)
        raise RuntimeError(f"Transbank respondió sin cuerpo (HTTP {response})")
    if not isinstance(response, dict):
        logger.error("Respuesta inesperada de Transbank status: %s", response)
        raise RuntimeError("Respuesta inesperada de Transbank")
    return {
        "authorized":  response.get("authorized", False),
        "voucher_url": response.get("voucherUrl", None),
    }

# =====================================================
#   REQUIRED SECRETS — fail-fast si falta algo crítico
# =====================================================
import os


def verify_required_secrets() -> None:
    """
    Aborta el arranque si falta un secreto crítico, en vez de dejar
    el endpoint correspondiente silenciosamente sin protección
    (mismo patrón que JWT_SECRET_KEY en src/auth_system.py).
    """
    if not (os.getenv("MP_WEBHOOK_TOKEN") or "").strip():
        raise RuntimeError(
            "❌ MP_WEBHOOK_TOKEN no definida — el webhook de Mercado Pago "
            "quedaría sin autenticación."
        )

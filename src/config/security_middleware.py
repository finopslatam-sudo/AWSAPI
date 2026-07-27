# =====================================================
#   SECURITY MIDDLEWARE — host allowlist + rate limiting
# =====================================================
import os
from flask import jsonify, request

from src.security.hardening import get_client_ip, is_allowed_host, rate_limiter

WEBHOOK_PATHS = {
    "/api/webhooks/paypal",
    "/api/webhooks/mercadopago",
}

ROUTE_LIMITS = {
    "/api/auth/login": (10, 60),
    "/api/auth/mfa/setup": (10, 300),
    "/api/auth/mfa/confirm": (10, 300),
    "/api/auth/mfa/verify": (10, 300),
    "/api/auth/mfa/recovery": (10, 300),
    "/api/auth/forgot-password": (5, 900),
    "/api/contact": (10, 600),
    "/api/payments/create-subscription": (12, 600),
    "/api/payments/mercadopago/subscription": (12, 600),
    "/api/patpass/create-inscription": (12, 600),
    "/api/patpass/confirm": (20, 600),
}


def register_security_guardrails(app) -> None:
    """Host allowlist + rate limiting global y por ruta sensible, antes de cada request."""

    @app.before_request
    def security_guardrails():
        if not is_allowed_host():
            return jsonify({"error": "Host no permitido"}), 400

        if request.method == "OPTIONS":
            return None

        path = request.path or ""

        if path in ("/up", "/api/health"):
            return None

        ip = get_client_ip()

        if path.startswith("/api/"):
            allowed, retry_after = rate_limiter.hit(
                key=f"api:{ip}",
                limit=int(os.getenv("RATE_LIMIT_API_PER_MINUTE", "300")),
                window_seconds=60,
            )
            if not allowed:
                return jsonify({
                    "error": "Demasiadas solicitudes. Intenta nuevamente en unos segundos."
                }), 429, {"Retry-After": str(retry_after)}

        # Webhooks externos no se limitan para evitar pérdida de eventos
        if path in WEBHOOK_PATHS:
            return None

        if path in ROUTE_LIMITS:
            limit, window = ROUTE_LIMITS[path]
            allowed, retry_after = rate_limiter.hit(
                key=f"route:{path}:{ip}",
                limit=limit,
                window_seconds=window,
            )
            if not allowed:
                return jsonify({
                    "error": "Demasiados intentos. Intenta nuevamente más tarde."
                }), 429, {"Retry-After": str(retry_after)}

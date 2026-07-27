# =====================================================
#   CORS CONFIG — orígenes permitidos y headers de respuesta
# =====================================================
import os
from flask import request
from flask_cors import CORS

from src.security.hardening import apply_security_headers


def get_allowed_origins() -> list[str]:
    """Calcula los orígenes permitidos desde env, o usa el default de prod + localhost."""
    raw = os.getenv("CORS_ALLOWED_ORIGINS")
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "https://finopslatam.com",
        "https://www.finopslatam.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def configure_cors(app, allowed_origins: list[str]) -> None:
    """Aplica CORS restringido a los orígenes explícitos y agrega headers de seguridad."""
    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        expose_headers=["Content-Type", "Authorization"],
    )

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")

        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin

        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers.setdefault("Vary", "Origin")

        apply_security_headers(response)

        return response

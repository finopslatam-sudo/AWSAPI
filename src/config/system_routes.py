# =====================================================
#   SYSTEM ROUTES — healthcheck, preflight CORS, raíz legacy
# =====================================================
from datetime import datetime
from flask import jsonify, request


def register_system_routes(app, allowed_origins: list[str]) -> None:

    @app.route('/api/health')
    def health():
        return jsonify({
            "status": "healthy",
            "service": "FinOps Latam API",
            "timestamp": datetime.utcnow().isoformat()
        })

    @app.route("/up")
    def up():
        return "ok", 200

    @app.route("/api/<path:path>", methods=["OPTIONS"])
    def handle_options(path):
        response = jsonify({"status": "ok"})

        origin = request.headers.get("Origin")
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"

        return response, 200

    @app.route('/')
    def pagina_principal():
        # Frontend manejado por Next.js — este backend no sirve HTML.
        return jsonify({"message": "Frontend manejado por Next.js"}), 404

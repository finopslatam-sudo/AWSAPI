# =====================================================
#   GLOBAL ERROR HANDLERS — nunca exponer detalles internos
# =====================================================
from flask import jsonify


def register_error_handlers(app) -> None:

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint no encontrado"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Método no permitido"}), 405

    @app.errorhandler(413)
    def payload_too_large(e):
        return jsonify({"error": "Payload demasiado grande"}), 413

    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({"error": "Demasiadas solicitudes"}), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"[500] Error interno: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

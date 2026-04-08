"""
ALERT ENGINE ROUTES
===================

Endpoint interno para disparar el motor de alertas.

Debe ser llamado por un cron job externo con el header:
  X-Internal-Secret: <INTERNAL_API_SECRET>

Configuración requerida en /etc/finops-api.env:
  INTERNAL_API_SECRET=un-secreto-largo-y-seguro

Ejemplo de cron (diario a las 08:00 AM):
  0 8 * * * curl -s -X POST https://api.finopslatam.com/api/internal/run-alerts \
    -H "X-Internal-Secret: <secret>" >> /var/log/finops-alerts.log
"""

import os
from flask import Blueprint, jsonify, request

from src.services.alert_engine import run_alert_engine


alert_engine_bp = Blueprint(
    "alert_engine",
    __name__,
    url_prefix="/api/internal"
)


@alert_engine_bp.route("/run-alerts", methods=["POST"])
def run_alerts():
    """
    Dispara el motor de evaluación de alertas.
    Protegido por secreto interno — no requiere JWT.
    """
    secret = request.headers.get("X-Internal-Secret", "")
    expected = os.environ.get("INTERNAL_API_SECRET", "")

    if not expected or secret != expected:
        return jsonify({"error": "Forbidden"}), 403

    try:
        result = run_alert_engine()
        return jsonify({"status": "ok", "result": result}), 200
    except Exception as e:
        print(f"[AlertEngineRoute] Error: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

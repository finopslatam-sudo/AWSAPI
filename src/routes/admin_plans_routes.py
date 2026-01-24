# =====================================================
# ADMIN PLANS ROUTES
# =====================================================
# Este archivo maneja:
# - Listado de planes (solo admin/root)
# - Obtención del plan del cliente (usado por el dashboard)
#
# IMPORTANTE:
# El endpoint /api/client/plan se define aquí para evitar
# crear nuevos archivos y romper la estructura actual.
# =====================================================

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.plan import Plan

# =====================================================
# BLUEPRINT
# =====================================================
admin_plans_bp = Blueprint(
    "admin_plans",
    __name__,
    url_prefix="/api"
)

def register_admin_plans_routes(app):
    app.register_blueprint(admin_plans_bp)

# =====================================================
# ADMIN — LISTAR PLANES (root / admin)
# GET /api/admin/plans
# =====================================================
@admin_plans_bp.route("/admin/plans", methods=["GET"])
@jwt_required()
def list_plans():
    user = User.query.get(int(get_jwt_identity()))

    if not user or user.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403

    plans = Plan.query.order_by(Plan.id.asc()).all()

    return jsonify({
        "plans": [
            {
                "id": p.id,
                "code": p.code,
                "name": p.name
            }
            for p in plans
        ]
    }), 200

# =====================================================
# CLIENT — OBTENER PLAN (dashboard)
# GET /api/client/plan
#
# NOTA:
# - Este endpoint evita el error de CORS (preflight 404)
# - Siempre devuelve un array
# - Permite que el frontend no crashee
# - La lógica real del plan se puede completar después
# =====================================================
@admin_plans_bp.route("/client/plan", methods=["GET", "OPTIONS"])
@jwt_required()
def get_client_plan():
    # Preflight CORS
    if request.method == "OPTIONS":
        return "", 200

    user = User.query.get(int(get_jwt_identity()))

    if not user:
        return jsonify([]), 200

    # Root / Admin no tienen plan de cliente
    if user.global_role in ("root", "admin"):
        return jsonify([]), 200

    # Usuario cliente sin client_id
    if not user.client_id:
        return jsonify([]), 200

    # Respuesta mínima segura
    # (puede ampliarse cuando exista relación client-plan)
    return jsonify([]), 200

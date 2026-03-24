# =====================================================
#   ENV (SAFE – NO ROMPE PROD)
# =====================================================
from dotenv import load_dotenv
import os

# Forzar override
if os.path.exists("/etc/finops-api.env"):
    load_dotenv("/etc/finops-api.env", override=False)
else:
    load_dotenv(override=True)
# =====================================================
#   CORE IMPORTS
# =====================================================
from flask import Flask, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from flask_cors import CORS

# =====================================================
#   APP INIT
# =====================================================
app = Flask(__name__)

# =====================================================
#   CORS (CONTROLADO)
# =====================================================

def _get_allowed_origins():
    """Compute allowed origins from env or default to prod + localhost."""
    raw = os.getenv("CORS_ALLOWED_ORIGINS")
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "https://finopslatam.com",
        "https://www.finopslatam.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

ALLOWED_ORIGINS = _get_allowed_origins()

CORS(
    app,
    resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
    supports_credentials=True,
    allow_headers=[
        "Content-Type",
        "Authorization"
    ],
    methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS"
    ],
    expose_headers=[
        "Content-Type",
        "Authorization"
    ]
)

@app.after_request
def add_cors_headers(response):

    origin = request.headers.get("Origin")

    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin

    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"

    return response

# =====================================================
#   DATABASE
# =====================================================
from src.models.database import init_db, db
# Import models to register them in metadata
from src.models.aws_account import AWSAccount
from src.models.aws_finding import AWSFinding
from src.models.tag_policy import TagPolicy
from src.models.aws_resource_inventory import AWSResourceInventory
from src.models.risk_snapshot import RiskSnapshot

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

if not app.config["SQLALCHEMY_DATABASE_URI"]:
    raise RuntimeError("❌ SQLALCHEMY_DATABASE_URI no definida")

init_db(app)

# =====================================================
#   DB SANITY CHECK (CRÍTICO EN PROD)
# =====================================================
with app.app_context():
    engine_url = str(db.engine.url)
    print(f"🔌 Connected DB: {engine_url}")

    require_prod_check = os.getenv("REQUIRE_PROD_DB_CHECK", "true").lower() == "true"

    if require_prod_check and "finops_prod" not in engine_url:
        raise RuntimeError(
            f"❌ API conectada a BD incorrecta: {engine_url}"
        )
# =====================================================
#   AUTH SYSTEM
# =====================================================
from src.auth_system import init_auth_system, create_auth_routes

init_auth_system(app)
create_auth_routes(app)

# =====================================================
#   ROUTES / BLUEPRINTS
# =====================================================
from src.routes.contact_routes import contact_bp
from src.routes.admin_clients_routes import register_admin_clients_routes
from src.routes.admin_reports_routes import register_admin_report_routes
from src.routes.admin_plans_routes import register_admin_plans_routes
from src.routes.client_reports_routes import register_client_report_routes
from src.routes.admin_stats_routes import admin_stats_bp
from src.routes.admin_users_routes import admin_users_bp
from src.routes.admin_user_access_routes import admin_user_access_bp
from src.routes.alert_policy_routes import alert_policy_bp
from src.routes.client_findings_routes import client_findings_bp
from src.routes.me_routes import me_bp
from src.routes.client_audit_routes import client_audit_bp
from src.routes.client_inventory_routes import client_inventory_bp
from src.routes.client_dashboard_routes import dashboard_bp
from src.routes.client_snapshot_routes import snapshot_bp
from src.routes.client_finops_routes import finops_bp
from src.routes.client_aws_connection_routes import client_aws_connection_bp
from src.routes.client_user_routes import client_users_bp
from src.routes.client_subscription_routes import client_subscription_bp
from src.routes.client_info_routes import client_info_bp
from src.routes.admin_plan_upgrade_routes import admin_plan_upgrade_bp
from src.routes.notification_routes import notification_bp
from src.routes.alert_engine_routes import alert_engine_bp
from src.routes.client_support_routes import client_support_bp
from src.routes.admin_support_routes import admin_support_bp
from src.models.notification import Notification  # noqa: F401 — expone tabla a Flask-Migrate
from src.models.support_ticket import SupportTicket, SupportTicketMessage  # noqa: F401 — expone tablas a Flask-Migrate

app.register_blueprint(snapshot_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(finops_bp)
app.register_blueprint(client_aws_connection_bp)
app.register_blueprint(client_inventory_bp)
app.register_blueprint(client_audit_bp)
app.register_blueprint(me_bp)
app.register_blueprint(client_findings_bp)
app.register_blueprint(contact_bp)
app.register_blueprint(admin_stats_bp)
app.register_blueprint(admin_users_bp)
app.register_blueprint(admin_user_access_bp)
app.register_blueprint(alert_policy_bp)
app.register_blueprint(client_users_bp)
app.register_blueprint(client_subscription_bp)
app.register_blueprint(client_info_bp)
app.register_blueprint(admin_plan_upgrade_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(alert_engine_bp)
app.register_blueprint(client_support_bp)
app.register_blueprint(admin_support_bp)

register_admin_clients_routes(app)
register_admin_report_routes(app)
register_admin_plans_routes(app)
register_client_report_routes(app)

# =====================================================
#   API HEALTHCHECK
# =====================================================
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

# =====================================================
#   GLOBAL OPTIONS HANDLER (CORS PREFLIGHT)
# =====================================================
@app.route("/api/<path:path>", methods=["OPTIONS"])
def handle_options(path):

    response = jsonify({"status": "ok"})

    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"

    return response, 200

# =====================================================
#   LEGACY FRONTEND (NO USAR)
# =====================================================
@app.route('/')
def pagina_principal():
    return jsonify({
        "message": "Frontend manejado por Next.js"
    }), 404

# =====================================================
#   GLOBAL ERROR HANDLERS
# =====================================================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint no encontrado"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Método no permitido"}), 405

@app.errorhandler(500)
def internal_error(e):
    app.logger.error(f"[500] Error interno: {e}")
    return jsonify({"error": "Error interno del servidor"}), 500

# =====================================================
#   RUN SERVER (DEV ONLY)
# =====================================================
if __name__ == '__main__':
    print("🚀 Iniciando FinOps Latam API")
    app.run(host='0.0.0.0', port=5001)

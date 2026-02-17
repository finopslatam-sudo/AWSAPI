# =====================================================
#   ENV (SAFE – NO ROMPE PROD)
# =====================================================
from dotenv import load_dotenv
import os

# Forzar override
if os.path.exists("/etc/finops-api.env"):
    load_dotenv("/etc/finops-api.env", override=True)
else:
    load_dotenv(override=True)
# =====================================================
#   CORE IMPORTS
# =====================================================
from flask import Flask, jsonify
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
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "https://www.finopslatam.com",
                "https://finopslatam.com"
            ],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Content-Type",
                "Authorization"
            ],
        }
    },
    supports_credentials=True
)

# =====================================================
#   DATABASE
# =====================================================
from src.models.database import init_db, db
# Import models to register them in metadata
from src.models.aws_account import AWSAccount
from src.models.aws_finding import AWSFinding
from src.models.tag_policy import TagPolicy

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

    if "finops_prod" not in engine_url:
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
from src.routes.aws_test_routes import aws_test_bp
from src.routes.client_findings_routes import client_findings_bp

app.register_blueprint(client_findings_bp)
app.register_blueprint(contact_bp)
app.register_blueprint(admin_stats_bp)
app.register_blueprint(admin_users_bp)
app.register_blueprint(aws_test_bp)

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

# =====================================================
#   DEBUG (SOLO DEV)
# =====================================================
if os.getenv("FLASK_DEBUG") == "1":
    @app.route("/debug/db")
    def debug_db():
        return {"db_engine": str(db.engine)}

# =====================================================
#   LEGACY FRONTEND (NO USAR)
# =====================================================
@app.route('/')
def pagina_principal():
    return jsonify({
        "message": "Frontend manejado por Next.js"
    }), 404

# =====================================================
#   RUN SERVER (DEV ONLY)
# =====================================================
if __name__ == '__main__':
    print("🚀 Iniciando FinOps Latam API")
    app.run(host='0.0.0.0', port=5001)

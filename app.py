# =====================================================
#   ENV (SAFE – NO ROMPE PROD)
# =====================================================
from dotenv import load_dotenv
load_dotenv()

# =====================================================
#   CORE IMPORTS
# =====================================================
from flask import Flask, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from flask_cors import CORS
import os

# =====================================================
#   APP INIT
# =====================================================
app = Flask(__name__)

# =====================================================
#   CORS (CONTROLADO)
# =====================================================
CORS(
    app,
    origins=[
        "https://www.finopslatam.com",
        "http://localhost:3000"
    ],
    supports_credentials=True
)

# =====================================================
#   DATABASE
# =====================================================
from src.models.database import init_db, db

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

if not app.config["SQLALCHEMY_DATABASE_URI"]:
    raise RuntimeError("❌ SQLALCHEMY_DATABASE_URI no definida")

init_db(app)

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
from src.routes.admin_users_routes import register_admin_users_routes
from src.routes.admin_clients_routes import register_admin_clients_routes
from src.routes.admin_reports_routes import register_admin_report_routes
from src.routes.admin_plans_routes import register_admin_plans_routes
from src.routes.client_reports_routes import register_client_report_routes
from src.routes.admin_stats_routes import admin_stats_bp

app.register_blueprint(contact_bp)
app.register_blueprint(admin_stats_bp)

register_admin_users_routes(app)
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

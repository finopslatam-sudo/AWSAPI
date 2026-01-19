# =====================================================
#   ENV (AGREGADO – NO ROMPE PROD)
# =====================================================
from dotenv import load_dotenv
load_dotenv()

# =====================================================
#   CORE IMPORTS
# =====================================================
from flask import Flask, jsonify, render_template, request, redirect
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    get_jwt_identity,
    create_access_token
)
from datetime import datetime
from flask_cors import CORS
import os
from sqlalchemy.exc import IntegrityError

# =====================================================
#   SMTP ENV VALIDATION (AJUSTE 2 - ENTERPRISE SAFE)
# =====================================================
required_envs = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS"]
missing = [v for v in required_envs if not os.getenv(v)]

if missing:
    print(f"⚠️ Variables SMTP faltantes: {missing}")
else:
    print("✅ Variables SMTP cargadas correctamente")

# =====================================================
#   ROUTES BLUEPRINTS
# =====================================================
from src.routes.contact_routes import contact_bp

# =====================================================
#   APP SERVICES
# =====================================================
from src.finops_auditor import FinOpsAuditor
from src.service_discovery import AWSServiceDiscovery

# =====================================================
#   AUTH SYSTEM
# =====================================================
from src.auth_system import (
    init_auth_system,
    create_auth_routes
)

# =====================================================
#   DATABASE
# =====================================================
from src.models.database import init_db, db
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan

# =====================================================
#   ROUTES MODULARES
# =====================================================
from src.routes.admin_reports_routes import register_admin_report_routes
from src.routes.client_reports_routes import register_client_report_routes
from src.routes.admin_users_routes import register_admin_users_routes

# =====================================================
#   APP INIT
# =====================================================
app = Flask(__name__)

# 👉 Blueprint de contacto
app.register_blueprint(contact_bp)

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
#   DATABASE CONFIG
# =====================================================
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

if not app.config["SQLALCHEMY_DATABASE_URI"]:
    raise RuntimeError("❌ SQLALCHEMY_DATABASE_URI no definida")

init_db(app)

# =====================================================
#   AUTH SYSTEM INIT
# =====================================================
init_auth_system(app)

register_admin_report_routes(app)
register_client_report_routes(app)
register_admin_users_routes(app)

# Evitar doble registro de rutas
if not os.getenv("FLASK_SKIP_ROUTES"):
    create_auth_routes(app)

# =====================================================
#   ADMIN - LISTAR PLANES
# =====================================================
@app.route('/api/admin/plans', methods=['GET'])
@jwt_required()
def admin_list_plans():
    admin_id = get_jwt_identity()
    admin = Client.query.get(admin_id)

    if not admin or admin.role != 'admin':
        return jsonify({"msg": "Unauthorized"}), 403

    plans = Plan.query.order_by(Plan.id.asc()).all()

    return jsonify({
        "plans": [
            {"id": p.id, "code": p.code, "name": p.name}
            for p in plans
        ]
    }), 200

# =====================================================
#   FRONTEND ROUTES
# =====================================================
def usuario_autenticado():
    try:
        get_jwt_identity()
        return True
    except Exception:
        return False

@app.route('/')
def pagina_principal():
    if usuario_autenticado():
        return redirect('/dashboard')
    return render_template('landing_public.html')

@app.route('/dashboard')
@jwt_required()
def dashboard():
    client_id = get_jwt_identity()
    client = Client.query.get(client_id)

    discovery = AWSServiceDiscovery()
    stats = discovery.get_filtered_service_statistics()

    return render_template(
        'dashboard.html',
        client=client,
        services=stats['services_in_use']
    )

# =====================================================
#   API ENDPOINTS
# =====================================================
@app.route('/api/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "FinOps Latam API",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/services/active')
def active_services():
    discovery = AWSServiceDiscovery()
    stats = discovery.get_filtered_service_statistics()
    return jsonify(stats)

# =====================================================
#   DEBUG
# =====================================================
@app.route("/debug/db")
def debug_db():
    return {"db_engine": str(db.engine)}

# =====================================================
#   RUN SERVER
# =====================================================
if __name__ == '__main__':
    print("🚀 Iniciando FinOps Latam API")
    app.run(host='0.0.0.0', port=5001)

# =====================================================
#   ENV (SAFE – NO ROMPE PROD)
# =====================================================
from src.config.env_loader import load_environment

load_environment()

# =====================================================
#   REQUIRED SECRETS (FAIL-FAST)
# =====================================================
from src.config.required_secrets import verify_required_secrets

verify_required_secrets()

# =====================================================
#   CORE IMPORTS
# =====================================================
import os
from flask import Flask

from src.config.cors_config import get_allowed_origins, configure_cors
from src.config.security_middleware import register_security_guardrails
from src.config.db_config import configure_database
from src.config.error_handlers import register_error_handlers
from src.config.system_routes import register_system_routes
from src.config.observability import init_observability

# =====================================================
#   APP INIT
# =====================================================
app = Flask(__name__)

init_observability()

ALLOWED_ORIGINS = get_allowed_origins()
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH_BYTES", str(64 * 1024)))

configure_cors(app, ALLOWED_ORIGINS)
register_security_guardrails(app)

# =====================================================
#   DATABASE
# =====================================================
configure_database(app)

# =====================================================
#   AUTH SYSTEM
# =====================================================
from src.auth.service import init_auth_system
from src.auth.routes import create_auth_routes

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
from src.routes.client_security_routes import client_security_bp
from src.routes.client_subscription_routes import client_subscription_bp
from src.routes.client_info_routes import client_info_bp
from src.routes.admin_plan_upgrade_routes import admin_plan_upgrade_bp
from src.routes.notification_routes import notification_bp
from src.routes.alert_engine_routes import alert_engine_bp
from src.routes.client_support_routes import client_support_bp
from src.routes.admin_support_routes import admin_support_bp
from src.routes.assistant_routes import assistant_bp
from src.routes.payments_routes import payments_bp
from src.routes.webhooks_routes import webhooks_bp
from src.routes.mercadopago_routes import mercadopago_bp
from src.routes.patpass_routes import patpass_bp

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
app.register_blueprint(client_security_bp)
app.register_blueprint(client_subscription_bp)
app.register_blueprint(client_info_bp)
app.register_blueprint(admin_plan_upgrade_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(alert_engine_bp)
app.register_blueprint(client_support_bp)
app.register_blueprint(admin_support_bp)
app.register_blueprint(assistant_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(webhooks_bp)
app.register_blueprint(mercadopago_bp)
app.register_blueprint(patpass_bp)

register_admin_clients_routes(app)
register_admin_report_routes(app)
register_admin_plans_routes(app)
register_client_report_routes(app)

# =====================================================
#   SYSTEM ROUTES / ERROR HANDLERS
# =====================================================
register_system_routes(app, ALLOWED_ORIGINS)
register_error_handlers(app)

# =====================================================
#   RUN SERVER (DEV ONLY)
# =====================================================
if __name__ == '__main__':
    print("🚀 Iniciando FinOps Latam API")
    app.run(host='0.0.0.0', port=5001)

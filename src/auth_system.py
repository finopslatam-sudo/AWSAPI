from flask import request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
import secrets
import string
from datetime import datetime, timedelta
import os

from src.models.database import db
from src.models.client import Client
from src.models.subscription import ClientSubscription
from src.models.plan import Plan

from src.services.admin_stats_service import get_admin_stats
from src.services.user_events_service import (
    on_user_deactivated,
    on_user_reactivated,
    on_admin_reset_password,
    on_password_changed,
    on_forgot_password,
    on_root_login,
    on_user_plan_changed 
)

# ===============================
# INIT EXTENSIONS
# ===============================
jwt = JWTManager()

# ===============================
# HELPERS
# ===============================
def generate_temp_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


def require_admin(client_id: int) -> bool:
    client = Client.query.get(client_id)
    return bool(client and client.role == "admin")


# ===============================
# INIT SYSTEM
# ===============================
def init_auth_system(app):
    app.config["JWT_SECRET_KEY"] = os.getenv(
        "JWT_SECRET_KEY", "finopslatam-prod-secret"
    )
    jwt.init_app(app)


# ===============================
# ROUTES
# ===============================
def create_auth_routes(app):

    # -------- LOGIN (CON EVENTOS) --------
    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        client = Client.query.filter_by(email=email, is_active=True).first()
        if not client or not client.check_password(password):
            return jsonify({"error": "Credenciales inválidas"}), 401

        # 🔐 Expiración de clave temporal
        if client.force_password_change and client.password_expires_at:
            if datetime.utcnow() > client.password_expires_at:
                return jsonify({"error": "Clave temporal expirada"}), 401

        # 🚨 EVENTO: LOGIN ROOT
        if client.is_root:
            on_root_login(client)

        token = create_access_token(identity=str(client.id))

        return jsonify({
            "access_token": token,
            "user": {
                "id": client.id,
                "email": client.email,
                "company_name": client.company_name,
                "contact_name": client.contact_name,
                "phone": client.phone,
                "role": client.role,
                "is_root": client.is_root,
                "is_active": client.is_active,
                "force_password_change": client.force_password_change
            }
        }), 200

    # ---------------------------------------------
    # ADMIN — ACTUALIZAR USUARIO
    # ---------------------------------------------
    @app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
    @jwt_required()
    def admin_update_user(user_id):
        admin_id = int(get_jwt_identity())
        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        data = request.get_json() or {}
        user = Client.query.get_or_404(user_id)

        previous_state = user.is_active

        user.company_name = data.get("company_name", user.company_name)
        user.contact_name = data.get("contact_name", user.contact_name)
        user.phone = data.get("phone", user.phone)
        user.email = data.get("email", user.email)

        if "is_active" in data:
            user.is_active = data["is_active"]

        db.session.commit()

        # 📧 EVENTOS DE ESTADO
        if previous_state and not user.is_active:
            on_user_deactivated(user)

        if not previous_state and user.is_active:
            user.force_password_change = True
            db.session.commit()
            on_user_reactivated(user)

        return jsonify({"message": "Usuario actualizado"}), 200
    
    # ---------------------------------------------
    # ADMIN — ACTUALIZAR PLAN DE USUARIO
    # ---------------------------------------------
    @app.route('/api/admin/users/<int:user_id>/plan', methods=['PUT'])
    @jwt_required()
    def admin_update_user_plan(user_id):
        admin_id = int(get_jwt_identity())
        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        data = request.get_json() or {}
        plan_id = data.get("plan_id")

        if not plan_id:
            return jsonify({"error": "plan_id es obligatorio"}), 400

        user = Client.query.get_or_404(user_id)

        # 🔎 Plan nuevo
        new_plan = Plan.query.get(plan_id)
        if not new_plan:
            return jsonify({"error": "Plan no encontrado"}), 404

        # 🔎 Suscripción actual (si existe)
        subscription = ClientSubscription.query.filter_by(
            client_id=user.id,
            is_active=True
        ).first()

        old_plan = subscription.plan if subscription else None

        if subscription:
            subscription.plan_id = new_plan.id
        else:
            subscription = ClientSubscription(
                client_id=user.id,
                plan_id=new_plan.id,
                is_active=True
            )
            db.session.add(subscription)

        db.session.commit()

        # 📧 EVENTO DE DOMINIO (CORRECTO)
        if old_plan:
            on_user_plan_changed(user, old_plan, new_plan)

        return jsonify({
            "message": "Plan actualizado correctamente",
            "user_id": user.id,
            "plan": {
                "id": new_plan.id,
                "code": new_plan.code,
                "name": new_plan.name
            }
        }), 200


    # ---------------------------------------------
    # CAMBIO PASSWORD USUARIO (VOLUNTARIO / FORZADO)
    # ---------------------------------------------
    @app.route('/api/auth/change-password', methods=['POST'])
    @jwt_required()
    def change_password():
        user = Client.query.get_or_404(int(get_jwt_identity()))
        data = request.get_json() or {}

        if not user.check_password(data.get("current_password")):
            return jsonify({"error": "Clave incorrecta"}), 400

        user.set_password(data["password"])
        user.force_password_change = False
        user.password_expires_at = None
        db.session.commit()

        on_password_changed(user)

        return jsonify({"message": "Contraseña actualizada"}), 200

    # ---------------------------------------------
    # FORGOT PASSWORD
    # ---------------------------------------------
    @app.route("/api/auth/forgot-password", methods=["POST"])
    def forgot_password():
        email = (request.get_json() or {}).get("email")
        user = Client.query.filter_by(email=email, is_active=True).first()

        if not user:
            return jsonify({"message": "Si existe, recibirás instrucciones"}), 200

        temp_password = generate_temp_password()
        user.set_password(temp_password)
        user.force_password_change = True
        user.password_expires_at = datetime.utcnow() + timedelta(minutes=30)
        db.session.commit()

        on_forgot_password(user, temp_password)

        return jsonify({"message": "Si existe, recibirás instrucciones"}), 200

    # ---------------------------------------------
    # ADMIN — RESET PASSWORD
    # ---------------------------------------------
    @app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
    @jwt_required()
    def admin_reset_password(user_id):
        admin_id = int(get_jwt_identity())
        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        user = Client.query.get_or_404(user_id)
        password = (request.get_json() or {}).get("password")

        user.set_password(password)
        user.force_password_change = True
        user.password_expires_at = datetime.utcnow() + timedelta(minutes=30)
        user.is_active = True
        db.session.commit()

        on_admin_reset_password(user, password)

        return jsonify({"message": "Password restablecida"}), 200

    # ---------------------------------------------
    # ADMIN — LISTAR USUARIOS (CON PLAN)
    # ---------------------------------------------
    @app.route('/api/admin/users', methods=['GET'])
    @jwt_required()
    def admin_list_users():
        admin_id = int(get_jwt_identity())
        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        users = (
            db.session.query(Client, ClientSubscription, Plan)
            .outerjoin(
                ClientSubscription,
                (Client.id == ClientSubscription.client_id)
                & (ClientSubscription.is_active == True)
            )
            .outerjoin(Plan, ClientSubscription.plan_id == Plan.id)
            .all()
        )

        return jsonify({
            "users": [
                {
                    "id": client.id,
                    "email": client.email,
                    "company_name": client.company_name,
                    "contact_name": client.contact_name,
                    "phone": client.phone,
                    "role": client.role,
                    "is_active": client.is_active,
                    "plan": {
                        "id": plan.id,
                        "code": plan.code,
                        "name": plan.name
                    } if plan else None
                }
                for client, subscription, plan in users
            ]
        }), 200

    # ---------------------------------------------
    # ADMIN — ESTADÍSTICAS
    # ---------------------------------------------
    @app.route('/api/admin/stats', methods=['GET'])
    @jwt_required()
    def admin_stats():
        admin_id = int(get_jwt_identity())
        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        return jsonify(get_admin_stats()), 200

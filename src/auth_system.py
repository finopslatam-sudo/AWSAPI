from flask import request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
import secrets
import string
from datetime import datetime, timedelta
import os
import logging

from src.models.database import db
from src.models.user import User

from src.services.user_events_service import (
    on_password_changed,
    on_forgot_password,
    on_root_login,
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

def require_staff(user_id: int) -> User | None:
    user = User.query.get(user_id)
    if not user:
        return None
    if user.global_role not in ("root", "support"):
        return None
    return user


def build_login_response(user):
    return {
        "id": user.id,
        "email": user.email,
        "global_role": user.global_role,
        "client_role": user.client_role,
        "client_id": user.client_id,
        "is_active": user.is_active,
        "force_password_change": user.force_password_change,
    }

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

        if not email or not password:
            return jsonify({"error": "Email y password requeridos"}), 400

        # 🔐 Autenticación CONTRA USERS
        user = User.query.filter_by(email=email).first()

        if not user or not user.is_active:
            return jsonify({"error": "Credenciales inválidas"}), 401

        # 🔑 Reutiliza el hash existente
        from werkzeug.security import check_password_hash
        if not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Credenciales inválidas"}), 401

        # 🚨 EVENTO: LOGIN ROOT (mantenido)
        if user.global_role == "root":
            try:
                ip = request.headers.get(
                    "X-Forwarded-For",
                    request.remote_addr
                )
                on_root_login(user, ip)
            except Exception as e:
                app.logger.error(f"[ROOT_LOGIN_ERROR] {e}")

        # 🪪 JWT con claims (SIN romper flask_jwt_extended)
        token = create_access_token(
            identity=str(user.id),
            additional_claims={
                "global_role": user.global_role,
                "client_role": user.client_role,
                "client_id": user.client_id
            }
        )

        return jsonify({
            "access_token": token,
            "user": build_login_response(user)
        }), 200


  
    # ---------------------------------------------
    # CAMBIO PASSWORD USUARIO (VOLUNTARIO / FORZADO)
    # ---------------------------------------------
    @app.route('/api/auth/change-password', methods=['POST'])
    @jwt_required()
    def change_password():
        user = User.query.get_or_404(int(get_jwt_identity()))
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
        user = User.query.filter_by(email=email, is_active=True).first()

        if not user:
            return jsonify({"message": "Si existe, recibirás instrucciones"}), 200

        temp_password = generate_temp_password()
        user.set_password(temp_password)
        user.force_password_change = True
        user.password_expires_at = datetime.utcnow() + timedelta(minutes=30)
        db.session.commit()

        on_forgot_password(user, temp_password)

        return jsonify({"message": "Si existe, recibirás instrucciones"}), 200

    

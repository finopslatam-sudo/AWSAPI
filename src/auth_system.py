from flask import request, jsonify
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from datetime import datetime
import os

from src.models.database import db
from src.models.user import User
from src.services.password_service import (
    generate_temp_password,
    get_temp_password_expiration
)
from src.services.user_events_service import (
    on_password_changed,
    on_forgot_password,
    on_root_login,
)
from zoneinfo import ZoneInfo

# ===============================
# INIT EXTENSIONS
# ===============================
jwt = JWTManager()

# ===============================
# JWT INIT
# ===============================
def init_auth_system(app):
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET_KEY no está configurado")

    app.config["JWT_SECRET_KEY"] = jwt_secret
    jwt.init_app(app)

# ===============================
# HELPERS
# ===============================
def build_login_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "global_role": user.global_role,
        "client_role": user.client_role,
        "client_id": user.client_id,
        "is_active": user.is_active,
        "force_password_change": user.force_password_change,
        "contact_name": user.contact_name,
    }

# ===============================
# ROUTES
# ===============================
def create_auth_routes(app):

    # -------- LOGIN --------
    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email y password requeridos"}), 400

        user = User.query.filter_by(email=email).first()

        if not user or not user.is_active:
            return jsonify({"error": "Credenciales inválidas"}), 401

        if not user.check_password(password):
            return jsonify({"error": "Credenciales inválidas"}), 401
        
        now = datetime.now(ZoneInfo("America/Santiago")).replace(tzinfo=None)

        if user.password_expires_at and user.password_expires_at < now:
            return jsonify({
                "error": "Password temporal expirado. Solicita un nuevo restablecimiento."
            }), 401

        # Evento especial para root
        if user.global_role == "root":
            try:
                ip = request.headers.get(
                    "X-Forwarded-For",
                    request.remote_addr
                )
                on_root_login(user, ip)
            except Exception as e:
                app.logger.error(f"[ROOT_LOGIN_ERROR] {e}")

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

    # -------- CHANGE PASSWORD --------
    @app.route('/api/auth/change-password', methods=['POST'])
    @jwt_required()
    def change_password():
        user = User.query.get_or_404(int(get_jwt_identity()))
        data = request.get_json() or {}

        # Aceptamos ambos nombres por compatibilidad
        current_password = (
            data.get("current_password")
            or data.get("currentPassword")
        )

        new_password = (
            data.get("password")
            or data.get("new_password")
            or data.get("newPassword")
        )

        if not current_password or not new_password:
            return jsonify({
                "error": "Datos incompletos"
            }), 400

        if not user.check_password(current_password):
            return jsonify({
                "error": "Clave actual incorrecta"
            }), 400

        user.set_password(new_password)
        user.force_password_change = False
        user.password_expires_at = None
        db.session.commit()

        on_password_changed(user)

        return jsonify({
            "message": "Contraseña actualizada correctamente"
        }), 200


    # -------- FORGOT PASSWORD --------
    @app.route("/api/auth/forgot-password", methods=["POST"])
    def forgot_password():
        email = (request.get_json() or {}).get("email")
        user = User.query.filter_by(email=email, is_active=True).first()

        if not user:
            return jsonify({"message": "Si existe, recibirás instrucciones"}), 200

        temp_password = generate_temp_password()
        user.set_password(temp_password)
        user.force_password_change = True
        user.password_expires_at = get_temp_password_expiration()

        db.session.commit()

        on_forgot_password(user, temp_password)

        return jsonify({"message": "Si existe, recibirás instrucciones"}), 200

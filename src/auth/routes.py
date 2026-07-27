# =====================================================
#   AUTH ROUTES — login, MFA, cambio/recuperación de password
# =====================================================
import os

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from src.models.database import db
from src.models.user import User
from src.security.hardening import get_client_ip, rate_limiter
from src.security.validation import is_valid_email, normalize_email
from src.services.mfa_service import (
    finalize_totp_enrollment,
    is_mfa_required_for_user,
    is_mfa_temporarily_locked,
    must_enroll_mfa,
    register_mfa_failure,
    register_mfa_success,
    start_totp_enrollment,
    verify_recovery_code,
    verify_user_totp,
)
from src.services.password_service import (
    generate_temp_password,
    get_temp_password_expiration,
)
from src.services.user_events_service import on_forgot_password, on_password_changed

from src.auth.service import (
    build_access_token,
    build_auth_success_response,
    build_challenge_response,
    build_login_response,
    resolve_user_from_challenge,
    validate_login_prerequisites,
)


def create_auth_routes(app):
    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json() or {}
        email = normalize_email(str(data.get("email", "")))
        password = str(data.get("password", ""))

        if not email or not password:
            return jsonify({"error": "Email y password requeridos"}), 400
        if not is_valid_email(email):
            return jsonify({"error": "Credenciales inválidas"}), 401

        ip = get_client_ip()
        fail_key = f"auth:login:fail:{email}:{ip}"
        max_fails = int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "10"))
        fail_window = int(os.getenv("AUTH_FAILED_WINDOW_SECONDS", "900"))

        if rate_limiter.count(fail_key, fail_window) >= max_fails:
            return jsonify({"error": "Demasiados intentos. Intenta nuevamente más tarde."}), 429

        user = User.query.filter_by(email=email).first()
        if not user or not user.is_active:
            rate_limiter.add(fail_key)
            return jsonify({"error": "Credenciales inválidas"}), 401

        if not user.check_password(password):
            rate_limiter.add(fail_key)
            return jsonify({"error": "Credenciales inválidas"}), 401

        rate_limiter.reset(fail_key)

        failed_prereq = validate_login_prerequisites(app, user, ip)
        if failed_prereq:
            return failed_prereq

        if must_enroll_mfa(user):
            return build_challenge_response(user, enrollment=True)

        if is_mfa_required_for_user(user):
            return build_challenge_response(user, enrollment=False)

        return build_auth_success_response(user)

    @app.route("/api/auth/mfa/setup", methods=["POST"])
    def auth_mfa_setup():
        data = request.get_json() or {}
        challenge_token = str(data.get("challenge_token", ""))

        if not challenge_token:
            return jsonify({"error": "challenge_token requerido"}), 400

        try:
            user = resolve_user_from_challenge(challenge_token)
        except ValueError:
            return jsonify({"error": "Challenge inválido o expirado"}), 401

        setup = start_totp_enrollment(user)
        db.session.commit()

        return jsonify({
            "secret": setup["secret"],
            "otpauth_url": setup["otpauth_url"],
            "challenge_token": challenge_token,
        }), 200

    @app.route("/api/auth/mfa/confirm", methods=["POST"])
    def auth_mfa_confirm():
        data = request.get_json() or {}
        challenge_token = str(data.get("challenge_token", ""))
        code = str(data.get("code", ""))

        if not challenge_token or not code:
            return jsonify({"error": "challenge_token y code son requeridos"}), 400

        try:
            user = resolve_user_from_challenge(challenge_token)
            recovery_codes = finalize_totp_enrollment(user, code)
            register_mfa_success(user)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            if str(exc) == "mfa_setup_not_started":
                return jsonify({"error": "Debes iniciar la configuración MFA primero"}), 400
            return jsonify({"error": "Código MFA inválido"}), 401

        return jsonify({
            "access_token": build_access_token(user),
            "user": build_login_response(user),
            "recovery_codes": recovery_codes,
        }), 200

    @app.route("/api/auth/mfa/verify", methods=["POST"])
    def auth_mfa_verify():
        data = request.get_json() or {}
        challenge_token = str(data.get("challenge_token", ""))
        code = str(data.get("code", ""))

        if not challenge_token or not code:
            return jsonify({"error": "challenge_token y code son requeridos"}), 400

        try:
            user = resolve_user_from_challenge(challenge_token)
        except ValueError:
            return jsonify({"error": "Challenge inválido o expirado"}), 401

        if is_mfa_temporarily_locked(user):
            return jsonify({"error": "MFA bloqueado temporalmente. Intenta nuevamente más tarde."}), 423

        if not user.mfa_enabled:
            return jsonify({"error": "Usuario sin MFA habilitado"}), 400

        if not verify_user_totp(user, code):
            register_mfa_failure(user)
            db.session.commit()
            return jsonify({"error": "Código MFA inválido"}), 401

        register_mfa_success(user)
        db.session.commit()
        return build_auth_success_response(user)

    @app.route("/api/auth/mfa/recovery", methods=["POST"])
    def auth_mfa_recovery():
        data = request.get_json() or {}
        challenge_token = str(data.get("challenge_token", ""))
        code = str(data.get("code", ""))

        if not challenge_token or not code:
            return jsonify({"error": "challenge_token y code son requeridos"}), 400

        try:
            user = resolve_user_from_challenge(challenge_token)
        except ValueError:
            return jsonify({"error": "Challenge inválido o expirado"}), 401

        if is_mfa_temporarily_locked(user):
            return jsonify({"error": "MFA bloqueado temporalmente. Intenta nuevamente más tarde."}), 423

        if not verify_recovery_code(user, code):
            register_mfa_failure(user)
            db.session.commit()
            return jsonify({"error": "Código de recuperación inválido"}), 401

        register_mfa_success(user)
        db.session.commit()
        return build_auth_success_response(user)

    @app.route("/api/auth/profile", methods=["GET"])
    @jwt_required()
    def auth_profile():
        user = User.query.get_or_404(int(get_jwt_identity()))
        return jsonify({"user": build_login_response(user)}), 200

    @app.route("/api/auth/change-password", methods=["POST"])
    @jwt_required()
    def change_password():
        user = User.query.get_or_404(int(get_jwt_identity()))
        data = request.get_json() or {}

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
            return jsonify({"error": "Datos incompletos"}), 400

        if not user.check_password(current_password):
            return jsonify({"error": "Clave actual incorrecta"}), 400

        user.set_password(new_password)
        user.force_password_change = False
        user.password_expires_at = None
        db.session.commit()

        on_password_changed(user)
        return jsonify({"message": "Contraseña actualizada correctamente"}), 200

    @app.route("/api/auth/forgot-password", methods=["POST"])
    def forgot_password():
        email = normalize_email(str((request.get_json() or {}).get("email", "")))
        ip = get_client_ip()

        if not email or not is_valid_email(email):
            return jsonify({"message": "Si existe, recibirás instrucciones"}), 200

        allowed, retry_after = rate_limiter.hit(
            key=f"auth:forgot:{email}:{ip}",
            limit=int(os.getenv("FORGOT_PASSWORD_MAX_ATTEMPTS", "5")),
            window_seconds=int(os.getenv("FORGOT_PASSWORD_WINDOW_SECONDS", "900")),
        )
        if not allowed:
            return jsonify({
                "message": "Si existe, recibirás instrucciones",
            }), 200, {"Retry-After": str(retry_after)}

        user = User.query.filter_by(email=email, is_active=True).first()
        if not user:
            return jsonify({"message": "Si existe, recibirás instrucciones"}), 200

        temp_password = generate_temp_password()
        user.set_password(temp_password)
        user.force_password_change = True
        user.password_expires_at = get_temp_password_expiration()
        user.mfa_pending_secret_encrypted = None
        db.session.commit()

        on_forgot_password(user, temp_password)
        return jsonify({"message": "Si existe, recibirás instrucciones"}), 200

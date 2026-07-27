# =====================================================
#   AUTH SERVICE — JWT init, tokens, respuestas de login
# =====================================================
from datetime import datetime, timedelta
import os

from flask import jsonify
from flask_jwt_extended import JWTManager, create_access_token
from zoneinfo import ZoneInfo

from src.models.plan import Plan
from src.models.subscription import ClientSubscription
from src.models.user import User
from src.services.mfa_service import (
    get_client_mfa_policy,
    is_mfa_required_for_user,
    is_mfa_temporarily_locked,
    issue_login_challenge,
    must_enroll_mfa,
    parse_login_challenge,
)
from src.services.user_events_service import on_root_login


jwt = JWTManager()


def init_auth_system(app):
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET_KEY no está configurado")

    app.config["JWT_SECRET_KEY"] = jwt_secret
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "120"))
    )
    jwt.init_app(app)


def get_user_plan_code(user: User):
    if not user.client_id:
        return None

    subscription = (
        ClientSubscription.query
        .filter_by(client_id=user.client_id, is_active=True)
        .first()
    )

    if not subscription:
        return None

    plan = Plan.query.get(subscription.plan_id)
    return plan.code if plan else None


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
        "plan_code": get_user_plan_code(user),
        "mfa_enabled": user.mfa_enabled,
        "mfa_policy": get_client_mfa_policy(user),
        "mfa_required_now": is_mfa_required_for_user(user) or must_enroll_mfa(user),
    }


def build_access_token(user: User) -> str:
    return create_access_token(
        identity=str(user.id),
        additional_claims={
            "global_role": user.global_role,
            "client_role": user.client_role,
            "client_id": user.client_id,
        },
    )


def build_auth_success_response(user: User):
    return jsonify({
        "access_token": build_access_token(user),
        "user": build_login_response(user),
    }), 200


def build_challenge_response(user: User, *, enrollment: bool):
    methods = ["totp"]
    if user.mfa_enabled:
        methods.append("recovery_code")

    payload = {
        "user": build_login_response(user),
        "challenge_token": issue_login_challenge(user),
        "mfa_policy": get_client_mfa_policy(user),
        "methods": methods,
    }

    if enrollment:
        payload["mfa_enrollment_required"] = True
        payload["message"] = "Debes configurar MFA antes de ingresar."
    else:
        payload["mfa_required"] = True
        payload["message"] = "Ingresa tu código MFA para continuar."

    return jsonify(payload), 200


def resolve_user_from_challenge(challenge_token: str) -> User:
    data = parse_login_challenge(challenge_token)
    user = User.query.get(int(data["user_id"]))
    if not user or not user.is_active:
        raise ValueError("challenge_invalid")
    return user


def validate_login_prerequisites(app, user: User, ip: str):
    now = datetime.now(ZoneInfo("America/Santiago")).replace(tzinfo=None)

    if user.password_expires_at and user.password_expires_at < now:
        return jsonify({
            "error": "Password temporal expirado. Solicita un nuevo restablecimiento.",
        }), 401

    if user.global_role == "root":
        try:
            on_root_login(user, ip)
        except Exception as exc:
            app.logger.error("[ROOT_LOGIN_ERROR] %s", exc)

    if is_mfa_temporarily_locked(user):
        return jsonify({
            "error": "MFA bloqueado temporalmente. Intenta nuevamente más tarde.",
        }), 423

    return None

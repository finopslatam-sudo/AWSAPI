from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from src.models.database import db
from src.models.plan import Plan
from src.models.subscription import ClientSubscription
from src.models.user import User
from src.services.mfa_service import (
    can_disable_mfa,
    disable_mfa,
    finalize_totp_enrollment,
    get_mfa_status,
    is_mfa_required_for_user,
    must_enroll_mfa,
    regenerate_recovery_codes,
    start_totp_enrollment,
)


me_bp = Blueprint("me", __name__, url_prefix="/api/me")


def _get_current_user() -> User:
    return User.query.get_or_404(int(get_jwt_identity()))


def _get_plan_code(user: User):
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


def _build_me_response(user: User) -> dict:
    mfa_status = get_mfa_status(user)
    return {
        "id": user.id,
        "email": user.email,
        "global_role": user.global_role,
        "client_role": user.client_role,
        "client_id": user.client_id,
        "is_active": user.is_active,
        "force_password_change": user.force_password_change,
        "contact_name": user.contact_name,
        "plan_code": _get_plan_code(user),
        "mfa_enabled": user.mfa_enabled,
        "mfa_policy": mfa_status["policy"],
        "mfa_required_now": is_mfa_required_for_user(user) or must_enroll_mfa(user),
        "mfa_confirmed_at": mfa_status["confirmed_at"],
        "mfa_last_used_at": mfa_status["last_used_at"],
        "mfa_has_recovery_codes": mfa_status["has_recovery_codes"],
    }


@me_bp.route("", methods=["GET"])
@jwt_required()
def get_me():
    user = _get_current_user()
    return jsonify(_build_me_response(user)), 200


@me_bp.route("", methods=["PUT"])
@jwt_required()
def update_me():
    user = _get_current_user()
    data = request.get_json() or {}

    if "email" in data:
        new_email = data["email"].strip().lower()
        if User.query.filter(User.email == new_email, User.id != user.id).first():
            return jsonify({"error": "Email ya en uso"}), 409
        user.email = new_email

    if "contact_name" in data:
        user.contact_name = data["contact_name"].strip()

    db.session.commit()
    return jsonify({
        "email": user.email,
        "contact_name": user.contact_name,
    }), 200


@me_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_my_password():
    user = _get_current_user()
    data = request.get_json() or {}

    if not user.check_password(data.get("current_password")):
        return jsonify({"error": "Password actual incorrecta"}), 400

    new_password = data.get("new_password")
    if not new_password or len(new_password) < 8:
        return jsonify({"error": "Password inválida"}), 400

    user.set_password(new_password)
    user.force_password_change = False
    user.password_expires_at = None
    db.session.commit()
    return jsonify({"ok": True}), 200


@me_bp.route("/security", methods=["GET"])
@jwt_required()
def get_my_security():
    user = _get_current_user()
    return jsonify({
        "mfa": get_mfa_status(user),
    }), 200


@me_bp.route("/mfa/setup", methods=["POST"])
@jwt_required()
def setup_my_mfa():
    user = _get_current_user()
    setup = start_totp_enrollment(user)
    db.session.commit()
    return jsonify(setup), 200


@me_bp.route("/mfa/confirm", methods=["POST"])
@jwt_required()
def confirm_my_mfa():
    user = _get_current_user()
    code = str((request.get_json() or {}).get("code", ""))
    if not code:
        return jsonify({"error": "code es requerido"}), 400

    try:
        recovery_codes = finalize_totp_enrollment(user, code)
        db.session.commit()
    except ValueError as exc:
        db.session.rollback()
        if str(exc) == "mfa_setup_not_started":
            return jsonify({"error": "Debes iniciar la configuración MFA primero"}), 400
        return jsonify({"error": "Código MFA inválido"}), 401

    return jsonify({
        "ok": True,
        "recovery_codes": recovery_codes,
        "mfa": get_mfa_status(user),
    }), 200


@me_bp.route("/mfa/disable", methods=["POST"])
@jwt_required()
def disable_my_mfa():
    user = _get_current_user()
    data = request.get_json() or {}
    current_password = str(data.get("current_password", ""))

    if not user.mfa_enabled:
        return jsonify({"error": "MFA no está habilitado"}), 400

    if not can_disable_mfa(user):
        return jsonify({"error": "La política actual exige MFA para este usuario"}), 403

    if not current_password or not user.check_password(current_password):
        return jsonify({"error": "Password actual incorrecta"}), 400

    disable_mfa(user)
    db.session.commit()
    return jsonify({
        "ok": True,
        "mfa": get_mfa_status(user),
    }), 200


@me_bp.route("/mfa/recovery-codes", methods=["POST"])
@jwt_required()
def regenerate_my_recovery_codes():
    user = _get_current_user()
    if not user.mfa_enabled:
        return jsonify({"error": "MFA no está habilitado"}), 400

    codes = regenerate_recovery_codes(user)
    db.session.commit()
    return jsonify({
        "recovery_codes": codes,
    }), 200

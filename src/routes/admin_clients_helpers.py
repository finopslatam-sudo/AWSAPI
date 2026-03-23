"""Helpers para las rutas de clientes admin (mantener archivo principal <300 líneas)."""

from flask import jsonify, current_app

from src.models.user import User
from src.models.client import Client
from src.models.plan import Plan
from src.models.subscription import ClientSubscription
from src.models.database import db


def _require_actor(actor: User | None):
    if not actor or actor.global_role not in ("root", "admin"):
        return jsonify({"error": "Unauthorized"}), 403
    return None, None


def _validate_create_payload(data: dict):
    company_name = data.get("company_name")
    email = data.get("email")
    contact_name = data.get("contact_name")
    phone = data.get("phone")
    is_active = data.get("is_active", True)
    plan_id = data.get("plan_id")
    owner_data = data.get("owner") or {}

    if not company_name:
        return None, (jsonify({"error": "company_name es obligatorio"}), 400)
    if not email:
        return None, (jsonify({"error": "email es obligatorio"}), 400)
    if not plan_id:
        return None, (jsonify({"error": "plan_id es obligatorio"}), 400)
    if not owner_data:
        return None, (jsonify({"error": "Owner obligatorio"}), 400)

    plan = Plan.query.get(plan_id)
    if not plan:
        return None, (jsonify({"error": "Plan no válido"}), 400)

    if Client.query.filter_by(email=email.strip().lower()).first():
        return None, (jsonify({"error": "Ya existe un cliente con ese email"}), 409)
    if Client.query.filter_by(company_name=company_name.strip()).first():
        return None, (jsonify({"error": "Ya existe un cliente con ese nombre"}), 409)

    owner_email = owner_data.get("email")
    owner_contact_name = owner_data.get("contact_name")
    password = owner_data.get("password")
    password_confirm = owner_data.get("password_confirm")

    if not owner_email or not owner_contact_name:
        return None, (jsonify({"error": "Datos de owner incompletos"}), 400)
    if not password or len(password) < 8:
        return None, (jsonify({"error": "Password inválida"}), 400)
    if password != password_confirm:
        return None, (jsonify({"error": "Las contraseñas no coinciden"}), 400)
    if User.query.filter_by(email=owner_email.strip().lower()).first():
        return None, (jsonify({"error": "El usuario owner ya existe"}), 409)

    payload = {
        "company_name": company_name.strip(),
        "email": email.strip().lower(),
        "contact_name": contact_name.strip() if contact_name else None,
        "phone": phone.strip() if phone else None,
        "is_active": is_active,
        "plan": plan,
        "owner_email": owner_email.strip().lower(),
        "owner_contact_name": owner_contact_name.strip(),
        "password": password,
    }
    return payload, None


def create_client_flow(data: dict, actor: User):
    error_resp, status = _require_actor(actor)
    if error_resp:
        return error_resp, status

    payload, error = _validate_create_payload(data)
    if error:
        return error

    plan = payload["plan"]
    try:
        client = Client(
            company_name=payload["company_name"],
            email=payload["email"],
            contact_name=payload["contact_name"],
            phone=payload["phone"],
            is_active=payload["is_active"],
        )
        db.session.add(client)
        db.session.flush()

        subscription = ClientSubscription(
            client_id=client.id,
            plan_id=plan.id,
            is_active=True,
        )
        db.session.add(subscription)

        owner = User(
            email=payload["owner_email"],
            contact_name=payload["owner_contact_name"],
            global_role=None,
            client_id=client.id,
            client_role="owner",
            is_active=True,
            force_password_change=True,
        )
        owner.set_password(payload["password"])
        db.session.add(owner)

        db.session.commit()

        from src.services.user_events_service import on_user_created_with_password

        try:
            on_user_created_with_password(owner, payload["password"])
        except Exception:
            current_app.logger.exception(
                "[OWNER_WELCOME_EMAIL_FAILED] user_id=%s",
                owner.id,
            )

        return jsonify({
            "data": {
                "client_id": client.id,
                "company_name": client.company_name,
                "owner_id": owner.id,
                "owner_email": owner.email,
                "plan": plan.name,
            }
        }), 201

    except Exception:
        db.session.rollback()
        current_app.logger.exception("[CREATE_CLIENT_FAILED]")
        return jsonify({"error": "Error interno"}), 500

from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.reports.admin.admin_users_provider import get_admin_users
from src.models.client import Client
from src.models.database import db
from src.services.email_service import send_email
from src.services.user_events_service import (
    on_user_deactivated,
    on_admin_reset_password,
    on_user_reactivated
)
from src.models.user import User
from src.models.subscription import ClientSubscription
from src.models.plan import Plan
def register_admin_users_routes(app):

    # ---------------------------------------------
    # ADMIN — LISTAR USUARIOS (ROOT / SUPPORT)
    # ---------------------------------------------
    @app.route('/api/admin/users', methods=['GET'])
    @jwt_required()
    def admin_list_users():
        actor_id = int(get_jwt_identity())

        actor = User.query.get(actor_id)
        if not actor:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # 🔐 Solo staff interno
        if actor.global_role not in ("root", "support"):
            return jsonify({"error": "Acceso denegado"}), 403

        users = (
            db.session.query(User, Client, ClientSubscription, Plan)
            .outerjoin(Client, User.client_id == Client.id)
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
                    "id": user.id,
                    "email": user.email,
                    "company_name": client.company_name if client else None,
                    "contact_name": user.contact_name,
                    "phone": user.phone,
                    "global_role": user.global_role,
                    "client_role": user.client_role,
                    "client_id": user.client_id,
                    "is_active": user.is_active,
                    "plan": {
                        "id": plan.id,
                        "code": plan.code,
                        "name": plan.name
                    } if plan else None
                }
                for user, client, subscription, plan in users
            ]
        }), 200


    # ============================
    # ACTUALIZAR USUARIO
    # ============================
    @app.route("/api/admin/users/<int:user_id>", methods=["PUT"])
    @jwt_required()
    def update_user(user_id):
        actor = Client.query.get(get_jwt_identity())
        target = Client.query.get(user_id)

        if not actor or not actor.is_active:
            return jsonify({"error": "Unauthorized"}), 403

        if not target:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # 🔒 BLOQUEO CRÍTICO
        if not target.can_be_modified_by(actor):
            return jsonify({
                "error": "No tienes permisos para modificar este usuario"
            }), 403

        data = request.get_json()

        target.company_name = data.get("company_name", target.company_name)
        target.contact_name = data.get("contact_name", target.contact_name)
        target.phone = data.get("phone", target.phone)
        target.email = data.get("email", target.email)
        target.role = data.get("role", target.role)
        # 🔎 Guardar estado anterior
        previous_state = target.is_active

        # 🔧 Actualizar estado
        target.is_active = data.get("is_active", target.is_active)

        db.session.commit()

        # 📧 EVENTOS DE ESTADO
        if previous_state is True and target.is_active is False:
            on_user_deactivated(target)

        if previous_state is False and target.is_active is True:
            on_user_reactivated(target)

        return jsonify({"message": "Usuario actualizado"}), 200

    # ============================
    # ELIMINAR (DESACTIVAR) USUARIO
    # ============================
    @app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
    def deactivate_user(user_id):
        target = Client.query.get(user_id)

        if not target:
            return jsonify({"error": "Usuario no encontrado"}), 404

        if not target.is_active:
            return jsonify({"message": "Usuario ya estaba desactivado"}), 200

        target.is_active = False
        db.session.commit()

        on_user_deactivated(target)

        return jsonify({"status": "ok"}), 200


    # ============================
    # RESET PASSWORD (ADMIN)
    # ============================
    @app.route("/api/admin/users/<int:user_id>/reset-password", methods=["POST"])
    @jwt_required()
    def reset_user_password(user_id):
        actor = Client.query.get(get_jwt_identity())
        target = Client.query.get(user_id)

        if not actor or not actor.is_active:
            return jsonify({"error": "Unauthorized"}), 403

        if not target:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # 🔒 BLOQUEO ROOT
        if not target.can_be_modified_by(actor):
            return jsonify({
                "error": "No puedes resetear la contraseña de este usuario"
            }), 403

        data = request.get_json() or {}
        new_password = data.get("password")

        if not new_password:
            return jsonify({"error": "Contraseña requerida"}), 400

        # 🔐 Cambio de password
        target.set_password(new_password)
        target.force_password_change = True

        db.session.commit()

        # 📧 EVENTO (ESTO ES LO QUE FALTABA)
        on_admin_reset_password(target, new_password)

        return jsonify({"message": "Contraseña actualizada"}), 200

from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.reports.admin.admin_users_provider import get_admin_users
from src.models.client import Client
from src.models.database import db
from src.services.email_service import send_email
from src.services.user_events_service import (
    on_user_deactivated,
    on_user_reactivated
)


def register_admin_users_routes(app):

    # ============================
    # LISTAR USUARIOS
    # ============================
    @app.route("/api/admin/users", methods=["GET"])
    @jwt_required()
    def admin_users():
        actor = Client.query.get(get_jwt_identity())

        if not actor or not actor.is_active:
            return jsonify({"error": "Unauthorized"}), 403

        if not (actor.is_root or actor.role == "admin"):
            return jsonify({"error": "Forbidden"}), 403

        users = get_admin_users()
        return jsonify({"users": users}), 200

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
    @app.route("/users/<int:user_id>/deactivate", methods=["POST"])
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
    # RESET PASSWORD
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

        data = request.get_json()
        target.set_password(data["password"])
        target.force_password_change = True

        db.session.commit()
        return jsonify({"message": "Contraseña actualizada"}), 200

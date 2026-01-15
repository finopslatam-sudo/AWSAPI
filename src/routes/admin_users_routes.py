from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.reports.admin.admin_users_provider import get_admin_users
from src.models.client import Client
from src.models.database import db


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
        target.is_active = data.get("is_active", target.is_active)

        db.session.commit()
        return jsonify({"message": "Usuario actualizado"}), 200

    # ============================
    # ELIMINAR (DESACTIVAR) USUARIO
    # ============================
    @app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
    @jwt_required()
    def delete_user(user_id):
        actor = Client.query.get(get_jwt_identity())
        target = Client.query.get(user_id)

        if not actor or not actor.is_active:
            return jsonify({"error": "Unauthorized"}), 403

        if not target:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # 🔒 BLOQUEO ROOT
        if not target.can_be_modified_by(actor):
            return jsonify({
                "error": "No puedes desactivar este usuario"
            }), 403

        target.is_active = False
        db.session.commit()

        return jsonify({"message": "Usuario desactivado"}), 200

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

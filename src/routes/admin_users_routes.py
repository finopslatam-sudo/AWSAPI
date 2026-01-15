from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.reports.admin.admin_users_provider import get_admin_users
from src.models.client import Client


def register_admin_users_routes(app):

    @app.route("/api/admin/users", methods=["GET"])
    @jwt_required()
    def admin_users():
        actor_id = get_jwt_identity()
        actor = Client.query.get(actor_id)

        # 🔒 Autenticación
        if not actor or not actor.is_active:
            return jsonify({"error": "Unauthorized"}), 403

        # 🔐 Autorización
        # ROOT (is_root=True) y ADMIN (role=admin) pueden listar usuarios
        if not (actor.is_root or actor.role == "admin"):
            return jsonify({"error": "Forbidden"}), 403

        users = get_admin_users()
        return jsonify({"users": users}), 200

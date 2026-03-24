"""
NOTIFICATION ROUTES
===================

GET    /api/notifications          → lista las últimas 30 notificaciones del usuario
PATCH  /api/notifications/{id}/read → marca una como leída
PATCH  /api/notifications/read-all  → marca todas como leídas
DELETE /api/notifications           → elimina todas las notificaciones leídas del usuario
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.notification import Notification
from src.models.database import db


notification_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/api/notifications"
)


# ─────────────────────────────────────────────────────────
# GET /api/notifications
# ─────────────────────────────────────────────────────────

@notification_bp.route("", methods=["GET"])
@jwt_required()
def list_notifications():

    user = User.query.get(int(get_jwt_identity()))

    if not user or not user.is_active:
        return jsonify({"error": "Acceso denegado"}), 403

    # Auto-purge notificaciones con más de 30 días
    cutoff = datetime.utcnow() - timedelta(days=30)
    Notification.query.filter(
        Notification.user_id == user.id,
        Notification.created_at < cutoff
    ).delete()
    db.session.commit()

    notifications = (
        Notification.query
        .filter_by(user_id=user.id)
        .order_by(Notification.created_at.desc())
        .limit(30)
        .all()
    )

    unread_count = (
        Notification.query
        .filter_by(user_id=user.id, is_read=False)
        .count()
    )

    return jsonify({
        "data": [n.to_dict() for n in notifications],
        "unread_count": unread_count,
    }), 200


# ─────────────────────────────────────────────────────────
# PATCH /api/notifications/{id}/read
# ─────────────────────────────────────────────────────────

@notification_bp.route("/<int:notification_id>/read", methods=["PATCH"])
@jwt_required()
def mark_read(notification_id):

    user = User.query.get(int(get_jwt_identity()))

    if not user or not user.is_active:
        return jsonify({"error": "Acceso denegado"}), 403

    notif = Notification.query.filter_by(
        id=notification_id,
        user_id=user.id
    ).first()

    if not notif:
        return jsonify({"error": "No encontrado"}), 404

    notif.is_read = True
    db.session.commit()

    return jsonify({"status": "ok"}), 200


# ─────────────────────────────────────────────────────────
# PATCH /api/notifications/read-all
# ─────────────────────────────────────────────────────────

@notification_bp.route("/read-all", methods=["PATCH"])
@jwt_required()
def mark_all_read():

    user = User.query.get(int(get_jwt_identity()))

    if not user or not user.is_active:
        return jsonify({"error": "Acceso denegado"}), 403

    Notification.query.filter_by(
        user_id=user.id,
        is_read=False
    ).update({"is_read": True})

    db.session.commit()

    return jsonify({"status": "ok"}), 200


# ─────────────────────────────────────────────────────────
# DELETE /api/notifications
# ─────────────────────────────────────────────────────────

@notification_bp.route("", methods=["DELETE"])
@jwt_required()
def clear_read():

    user = User.query.get(int(get_jwt_identity()))

    if not user or not user.is_active:
        return jsonify({"error": "Acceso denegado"}), 403

    deleted = Notification.query.filter_by(
        user_id=user.id,
        is_read=True
    ).delete()

    db.session.commit()

    return jsonify({"status": "ok", "deleted": deleted}), 200

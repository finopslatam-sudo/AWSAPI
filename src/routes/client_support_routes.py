"""
CLIENT SUPPORT ROUTES
=====================
GET  /api/client/support/tickets           → lista tickets del cliente
POST /api/client/support/tickets           → crear ticket
GET  /api/client/support/tickets/<id>      → detalle + mensajes
POST /api/client/support/tickets/<id>/messages  → agregar mensaje
PATCH /api/client/support/tickets/<id>/close    → cerrar ticket
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.database import db
from src.models.user import User
from src.models.support_ticket import SupportTicket, SupportTicketMessage


client_support_bp = Blueprint(
    "client_support",
    __name__,
    url_prefix="/api/client/support"
)
client_support_bp.strict_slashes = False


# ─────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────

def _require_client(user_id: int) -> User | None:
    user = User.query.get(int(user_id))
    if not user or not user.is_active:
        return None
    if user.global_role is not None:
        return None
    if not user.client_id:
        return None
    return user


# ─────────────────────────────────────────────────────────
# GET /api/client/support/tickets
# ─────────────────────────────────────────────────────────

@client_support_bp.route("/tickets", methods=["GET"])
@jwt_required()
def list_tickets():
    user = _require_client(get_jwt_identity())
    if not user:
        return jsonify({"error": "Acceso denegado"}), 403

    status_filter = request.args.get("status", "").strip()

    q = SupportTicket.query.filter_by(client_id=user.client_id)
    if status_filter:
        q = q.filter_by(status=status_filter)

    tickets = q.order_by(SupportTicket.created_at.desc()).all()

    return jsonify({"data": [t.to_dict() for t in tickets]}), 200


# ─────────────────────────────────────────────────────────
# POST /api/client/support/tickets
# ─────────────────────────────────────────────────────────

@client_support_bp.route("/tickets", methods=["POST"])
@jwt_required()
def create_ticket():
    user = _require_client(get_jwt_identity())
    if not user:
        return jsonify({"error": "Acceso denegado"}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    title       = str(data.get("title", "")).strip()[:255]
    description = str(data.get("description", "")).strip()
    priority    = str(data.get("priority", "medium")).strip()

    if not title:
        return jsonify({"error": "El título es requerido"}), 400
    if not description:
        return jsonify({"error": "La descripción es requerida"}), 400
    if priority not in ("low", "medium", "high", "critical"):
        priority = "medium"

    try:
        ticket = SupportTicket(
            ticket_number="TKT-PENDING",
            client_id=user.client_id,
            user_id=user.id,
            title=title,
            description=description,
            priority=priority,
            status="open",
        )
        db.session.add(ticket)
        db.session.flush()  # obtener ID antes de commit

        ticket.ticket_number = f"TKT-{datetime.utcnow().year}-{ticket.id:05d}"
        db.session.commit()

        return jsonify({"status": "ok", "ticket": ticket.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[support] create_ticket error: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


# ─────────────────────────────────────────────────────────
# GET /api/client/support/tickets/<id>
# ─────────────────────────────────────────────────────────

@client_support_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@jwt_required()
def get_ticket(ticket_id: int):
    user = _require_client(get_jwt_identity())
    if not user:
        return jsonify({"error": "Acceso denegado"}), 403

    ticket = SupportTicket.query.filter_by(
        id=ticket_id, client_id=user.client_id
    ).first()

    if not ticket:
        return jsonify({"error": "No encontrado"}), 404

    return jsonify({"ticket": ticket.to_dict(include_messages=True)}), 200


# ─────────────────────────────────────────────────────────
# POST /api/client/support/tickets/<id>/messages
# ─────────────────────────────────────────────────────────

@client_support_bp.route("/tickets/<int:ticket_id>/messages", methods=["POST"])
@jwt_required()
def add_message(ticket_id: int):
    user = _require_client(get_jwt_identity())
    if not user:
        return jsonify({"error": "Acceso denegado"}), 403

    ticket = SupportTicket.query.filter_by(
        id=ticket_id, client_id=user.client_id
    ).first()

    if not ticket:
        return jsonify({"error": "No encontrado"}), 404

    if ticket.status == "closed":
        return jsonify({"error": "El ticket está cerrado"}), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    body = str(data.get("body", "")).strip()
    if not body:
        return jsonify({"error": "El mensaje no puede estar vacío"}), 400
    if len(body) > 5000:
        return jsonify({"error": "El mensaje es demasiado largo"}), 400

    try:
        msg = SupportTicketMessage(
            ticket_id=ticket.id,
            user_id=user.id,
            is_staff=False,
            author_name=user.contact_name or user.email,
            body=body,
        )
        db.session.add(msg)

        if ticket.status == "resolved":
            ticket.status = "open"

        ticket.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"status": "ok", "message": msg.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[support] add_message error: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


# ─────────────────────────────────────────────────────────
# PATCH /api/client/support/tickets/<id>/close
# ─────────────────────────────────────────────────────────

@client_support_bp.route("/tickets/<int:ticket_id>/close", methods=["PATCH"])
@jwt_required()
def close_ticket(ticket_id: int):
    user = _require_client(get_jwt_identity())
    if not user:
        return jsonify({"error": "Acceso denegado"}), 403

    ticket = SupportTicket.query.filter_by(
        id=ticket_id, client_id=user.client_id
    ).first()

    if not ticket:
        return jsonify({"error": "No encontrado"}), 404

    if ticket.status == "closed":
        return jsonify({"error": "El ticket ya está cerrado"}), 400

    ticket.status = "closed"
    ticket.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"status": "ok"}), 200

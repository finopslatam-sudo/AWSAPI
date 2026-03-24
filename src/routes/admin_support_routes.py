"""
ADMIN SUPPORT ROUTES
====================
GET   /api/admin/support/tickets              → listar todos los tickets
GET   /api/admin/support/tickets/<id>         → detalle + mensajes
POST  /api/admin/support/tickets/<id>/messages → responder ticket
PATCH /api/admin/support/tickets/<id>/status   → cambiar estado
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.database import db
from src.models.user import User
from src.models.support_ticket import SupportTicket, SupportTicketMessage
from src.models.notification import Notification


admin_support_bp = Blueprint(
    "admin_support",
    __name__,
    url_prefix="/api/admin/support"
)
admin_support_bp.strict_slashes = False


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _require_staff(user_id: int) -> User | None:
    user = User.query.get(int(user_id))
    if not user or not user.is_active:
        return None
    if user.global_role not in ("root", "admin", "support"):
        return None
    return user


def _notify_ticket_owner(ticket: SupportTicket, title: str, message: str, ntype: str) -> None:
    db.session.add(Notification(
        user_id=ticket.user_id, type=ntype,
        title=title, message=message, reference_id=ticket.id,
    ))


# ─────────────────────────────────────────────────────────
# GET /api/admin/support/tickets
# ─────────────────────────────────────────────────────────

@admin_support_bp.route("/tickets", methods=["GET"])
@jwt_required()
def list_tickets():
    staff = _require_staff(get_jwt_identity())
    if not staff:
        return jsonify({"error": "Acceso denegado"}), 403

    status_filter   = request.args.get("status", "").strip()
    priority_filter = request.args.get("priority", "").strip()
    client_filter   = request.args.get("client_id", "").strip()

    q = SupportTicket.query

    if status_filter:
        q = q.filter_by(status=status_filter)
    if priority_filter:
        q = q.filter_by(priority=priority_filter)
    if client_filter and client_filter.isdigit():
        q = q.filter_by(client_id=int(client_filter))

    tickets = q.order_by(SupportTicket.created_at.desc()).all()

    # Incluir nombre de empresa en cada ticket
    from src.models.client import Client
    client_names: dict[int, str] = {}

    result = []
    for t in tickets:
        d = t.to_dict()
        if t.client_id not in client_names:
            c = Client.query.get(t.client_id)
            client_names[t.client_id] = c.company_name if c else "—"
        d["company_name"] = client_names[t.client_id]
        result.append(d)

    return jsonify({"data": result}), 200


# ─────────────────────────────────────────────────────────
# GET /api/admin/support/tickets/<id>
# ─────────────────────────────────────────────────────────

@admin_support_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@jwt_required()
def get_ticket(ticket_id: int):
    staff = _require_staff(get_jwt_identity())
    if not staff:
        return jsonify({"error": "Acceso denegado"}), 403

    ticket = SupportTicket.query.get(ticket_id)
    if not ticket:
        return jsonify({"error": "No encontrado"}), 404

    from src.models.client import Client
    c = Client.query.get(ticket.client_id)

    data = ticket.to_dict(include_messages=True)
    data["company_name"] = c.company_name if c else "—"

    return jsonify({"ticket": data}), 200


# ─────────────────────────────────────────────────────────
# POST /api/admin/support/tickets/<id>/messages
# ─────────────────────────────────────────────────────────

@admin_support_bp.route("/tickets/<int:ticket_id>/messages", methods=["POST"])
@jwt_required()
def add_message(ticket_id: int):
    staff = _require_staff(get_jwt_identity())
    if not staff:
        return jsonify({"error": "Acceso denegado"}), 403

    ticket = SupportTicket.query.get(ticket_id)
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
            user_id=staff.id,
            is_staff=True,
            author_name=staff.contact_name or staff.email,
            body=body,
        )
        db.session.add(msg)

        ticket.status = "in_progress"
        ticket.assigned_to_id = staff.id
        ticket.updated_at = datetime.utcnow()

        _notify_ticket_owner(
            ticket,
            title=f"Respuesta en {ticket.ticket_number}",
            message=f"El equipo de soporte ha respondido tu ticket '{ticket.title[:60]}'.",
            ntype="support_ticket_reply",
        )

        db.session.commit()

        return jsonify({"status": "ok", "message": msg.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"[admin_support] add_message error: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


# ─────────────────────────────────────────────────────────
# PATCH /api/admin/support/tickets/<id>/status
# ─────────────────────────────────────────────────────────

@admin_support_bp.route("/tickets/<int:ticket_id>/status", methods=["PATCH"])
@jwt_required()
def update_status(ticket_id: int):
    staff = _require_staff(get_jwt_identity())
    if not staff:
        return jsonify({"error": "Acceso denegado"}), 403

    ticket = SupportTicket.query.get(ticket_id)
    if not ticket:
        return jsonify({"error": "No encontrado"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Payload inválido"}), 400

    new_status = str(data.get("status", "")).strip()
    valid = ("open", "in_progress", "resolved", "closed")
    if new_status not in valid:
        return jsonify({"error": f"Estado inválido. Valores permitidos: {valid}"}), 400

    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()

    if new_status == "resolved":
        ticket.resolved_at = datetime.utcnow()
        ticket.assigned_to_id = staff.id

    _status_labels = {
        "resolved": "resuelto",
        "closed":   "cerrado",
        "open":     "reabierto",
        "in_progress": "en proceso",
    }
    if new_status in ("resolved", "closed", "open", "in_progress"):
        _notify_ticket_owner(
            ticket,
            title=f"Ticket {ticket.ticket_number} {_status_labels[new_status]}",
            message=f"El estado de tu ticket '{ticket.title[:60]}' cambió a {_status_labels[new_status]}.",
            ntype="support_ticket_status",
        )

    db.session.commit()

    return jsonify({"status": "ok", "ticket": ticket.to_dict()}), 200

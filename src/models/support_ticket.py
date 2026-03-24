"""
SUPPORT TICKET MODEL
====================
Sistema de tickets de soporte para clientes.

Estados:
- open         → recién creado, sin respuesta
- in_progress  → staff lo está atendiendo
- resolved     → resuelto por staff
- closed       → cerrado por el cliente

Prioridades:
- low / medium / high / critical
"""

from datetime import datetime
from src.models.database import db


class SupportTicket(db.Model):
    __tablename__ = "support_tickets"

    id              = db.Column(db.Integer,      primary_key=True)
    ticket_number   = db.Column(db.String(20),   unique=True, nullable=False, index=True)
    client_id       = db.Column(db.Integer,      db.ForeignKey("clients.id"), nullable=False, index=True)
    user_id         = db.Column(db.Integer,      db.ForeignKey("users.id"),   nullable=False)
    title           = db.Column(db.String(255),  nullable=False)
    description     = db.Column(db.Text,         nullable=False)
    status          = db.Column(db.String(20),   nullable=False, default="open")
    priority        = db.Column(db.String(20),   nullable=False, default="medium")
    assigned_to_id  = db.Column(db.Integer,      db.ForeignKey("users.id"),   nullable=True)
    created_at      = db.Column(db.DateTime,     nullable=False, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime,     nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at     = db.Column(db.DateTime,     nullable=True)

    messages = db.relationship(
        "SupportTicketMessage",
        backref="ticket",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_messages: bool = False) -> dict:
        data = {
            "id":             self.id,
            "ticket_number":  self.ticket_number,
            "client_id":      self.client_id,
            "user_id":        self.user_id,
            "title":          self.title,
            "description":    self.description,
            "status":         self.status,
            "priority":       self.priority,
            "assigned_to_id": self.assigned_to_id,
            "created_at":     self.created_at.isoformat(),
            "updated_at":     self.updated_at.isoformat(),
            "resolved_at":    self.resolved_at.isoformat() if self.resolved_at else None,
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages.order_by(SupportTicketMessage.created_at.asc())]
        return data


class SupportTicketMessage(db.Model):
    __tablename__ = "support_ticket_messages"

    id         = db.Column(db.Integer,  primary_key=True)
    ticket_id  = db.Column(db.Integer,  db.ForeignKey("support_tickets.id"), nullable=False, index=True)
    user_id    = db.Column(db.Integer,  db.ForeignKey("users.id"),           nullable=False)
    is_staff   = db.Column(db.Boolean,  nullable=False, default=False)
    author_name= db.Column(db.String(120), nullable=True)
    body       = db.Column(db.Text,     nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "ticket_id":   self.ticket_id,
            "user_id":     self.user_id,
            "is_staff":    self.is_staff,
            "author_name": self.author_name,
            "body":        self.body,
            "created_at":  self.created_at.isoformat(),
        }

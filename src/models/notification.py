"""
NOTIFICATION MODEL
==================
Notificaciones en-app por usuario.

Tipos soportados:
- plan_upgrade_requested  → staff: un cliente solicitó upgrade
- plan_upgrade_approved   → cliente: su plan fue aprobado
- plan_upgrade_rejected   → cliente: su solicitud fue rechazada
"""

from datetime import datetime
from src.models.database import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type       = db.Column(db.String(64),  nullable=False)
    title      = db.Column(db.String(255), nullable=False)
    message    = db.Column(db.Text,        nullable=False)
    is_read    = db.Column(db.Boolean,     nullable=False, default=False)
    created_at = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "type":       self.type,
            "title":      self.title,
            "message":    self.message,
            "is_read":    self.is_read,
            "created_at": self.created_at.isoformat(),
        }

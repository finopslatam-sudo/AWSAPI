"""
PLAN CHANGE EVENT MODEL
=======================

Registro de cambios de plan de clientes.

Permite:
- auditoría
- historial de facturación
- soporte
- métricas SaaS
"""

from datetime import datetime
from src.models.database import db


class PlanChangeEvent(db.Model):

    __tablename__ = "plan_change_events"

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    old_plan = db.Column(
        db.String(100),
        nullable=False
    )

    new_plan = db.Column(
        db.String(100),
        nullable=False
    )

    changed_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )
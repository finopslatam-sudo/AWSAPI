"""
CLIENT SUBSCRIPTION MODEL
=========================

Representa la suscripción de un cliente a un plan FinOps.

- Un cliente puede tener múltiples suscripciones históricas
- Solo una debe estar activa (is_active = True)
"""

from datetime import datetime
from src.models.database import db


class ClientSubscription(db.Model):
    __tablename__ = "client_subscriptions"

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    plan_id = db.Column(
        db.Integer,
        db.ForeignKey("plans.id"),
        nullable=False
    )

    # Indica la suscripción activa del cliente
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

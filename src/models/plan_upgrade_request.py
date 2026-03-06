"""
PLAN UPGRADE REQUEST MODEL
==========================

Solicitudes de upgrade de plan realizadas por clientes.
Requiere aprobación de admin.
"""

from datetime import datetime
from src.models.database import db


class PlanUpgradeRequest(db.Model):

    __tablename__ = "plan_upgrade_requests"

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    requested_plan = db.Column(
        db.String(50),
        nullable=False
    )

    requested_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        default="PENDING",
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    approved_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    approved_at = db.Column(
        db.DateTime
    )
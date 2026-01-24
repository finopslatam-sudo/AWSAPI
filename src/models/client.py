"""
CLIENT MODEL
============

Representa una empresa cliente dentro de la plataforma FinOpsLatam.

IMPORTANTE:
- Este modelo debe reflejar EXACTAMENTE la tabla `clients`
- No contiene lógica de negocio
- No gestiona usuarios ni suscripciones
"""

from datetime import datetime
from src.models.database import db


class Client(db.Model):
    __tablename__ = "clients"

    # ==========================
    # PRIMARY KEY
    # ==========================
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # ==========================
    # CLIENT DATA
    # ==========================
    company_name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True
    )

    contact_name = db.Column(
        db.String(100),
        nullable=True
    )

    phone = db.Column(
        db.String(20),
        nullable=True
    )

    # ==========================
    # STATUS
    # ==========================
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=True
    )

    # ==========================
    # AUDIT
    # ==========================
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=True
    )

    def __repr__(self) -> str:
        return f"<Client {self.company_name}>"

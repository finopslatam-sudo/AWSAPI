"""
CLIENT MODEL
============

Representa una empresa cliente (tenant) del SaaS FinOpsLatam.

- Un cliente puede tener múltiples usuarios
- El estado is_active controla el acceso de toda la empresa
"""

from datetime import datetime
from src.models.database import db


class Client(db.Model):
    __tablename__ = "clients"

    # ==========================
    # CORE FIELDS (EMPRESA)
    # ==========================
    id = db.Column(db.Integer, primary_key=True)

    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    contact_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)

    # Estado del cliente (afecta a todos sus usuarios)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # ==========================
    # RELATIONSHIPS
    # ==========================
    users = db.relationship(
        "User",
        backref="client",
        lazy=True,
        cascade="all, delete-orphan"
    )

    # ==========================
    # SERIALIZATION
    # ==========================
    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "email": self.email,
            "contact_name": self.contact_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self):
        return f"<Client {self.company_name}>"

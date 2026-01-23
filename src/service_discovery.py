"""
AWS ACCOUNT MODEL
=================

Representa una cuenta AWS asociada a un cliente FinOpsLatam.

- Un cliente puede tener múltiples cuentas AWS
- Se utiliza para auditorías, métricas y optimización FinOps
- La integración se realiza vía AssumeRole
"""

from datetime import datetime
from src.models.database import db


class AWSAccount(db.Model):
    __tablename__ = "aws_accounts"

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    # Identificación AWS
    account_id = db.Column(
        db.String(12),
        nullable=False
    )

    account_name = db.Column(
        db.String(100),
        nullable=False
    )

    # Seguridad AWS
    role_arn = db.Column(
        db.String(255),
        nullable=False
    )

    external_id = db.Column(
        db.String(255),
        nullable=True
    )

    # Estado
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    # Sincronización
    last_sync = db.Column(
        db.DateTime,
        nullable=True
    )

    # Auditoría
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "account_name": self.account_name,
            "is_active": self.is_active,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "created_at": self.created_at.isoformat(),
        }

"""
USER MODEL
==========

Representa un usuario del sistema FinOpsLatam.

Tipos de usuario:
- Global (staff):
    - root
    - admin
- Usuario de cliente:
    - asociado a un client_id
    - con client_role definido

IMPORTANTE:
- global_role define permisos a nivel plataforma
- client_role define permisos dentro de un cliente
"""

from datetime import datetime
from .database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    # ==========================
    # ROLES
    # ==========================
    global_role = db.Column(
        db.String(50),
        nullable=True
    )
    # Valores válidos:
    # - root
    # - admin
    # - None (usuario de cliente)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=True
    )

    client_role = db.Column(
        db.String(50),
        nullable=True
    )
    # Valores válidos (usuarios de cliente):
    # - finops_admin
    # - viewer

    # ==========================
    # SECURITY FLAGS
    # ==========================
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    force_password_change = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    password_expires_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # ==========================
    # AUDIT
    # ==========================
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f"<User {self.email}>"

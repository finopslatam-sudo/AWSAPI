"""
PLAN MODEL
==========

Representa un plan FinOps disponible en la plataforma.

Este modelo actúa como un catálogo:
- No contiene lógica de negocio
- No define estados
- No define precios
"""

from src.models.database import db


class Plan(db.Model):
    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

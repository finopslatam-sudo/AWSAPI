"""
PATPASS INSCRIPTION MODEL
=========================
Registra cada inscripción de suscripción procesada a través de PatPass Comercio (Transbank).

Estados:
- pending   : inscripción iniciada, esperando autorización del cliente en Transbank
- active    : inscripción confirmada, tbk_user disponible para cobros mensuales
- rejected  : Transbank rechazó la inscripción
- cancelled : suscripción cancelada
"""

from datetime import datetime
from src.models.database import db


class PatpassInscription(db.Model):
    __tablename__ = "patpass_inscriptions"

    id               = db.Column(db.Integer,     primary_key=True)
    email            = db.Column(db.String(320), nullable=False, index=True)
    nombre           = db.Column(db.String(255), nullable=True)
    empresa          = db.Column(db.String(255), nullable=True)
    pais             = db.Column(db.String(100), nullable=True)
    telefono         = db.Column(db.String(50),  nullable=True)
    plan_code        = db.Column(db.String(50),  nullable=False)
    plan_name        = db.Column(db.String(100), nullable=False)
    buy_order        = db.Column(db.String(100), nullable=False, unique=True, index=True)
    tbk_user         = db.Column(db.String(255), nullable=True)   # token para cobros futuros
    amount_clp       = db.Column(db.Integer,     nullable=False)
    authorization_code = db.Column(db.String(50), nullable=True)
    card_type        = db.Column(db.String(50),  nullable=True)
    card_last_four   = db.Column(db.String(10),  nullable=True)
    status           = db.Column(db.String(50),  nullable=False, default="pending")
    created_at       = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow)
    confirmed_at     = db.Column(db.DateTime,    nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "email":        self.email,
            "nombre":       self.nombre,
            "empresa":      self.empresa,
            "pais":         self.pais,
            "plan_code":    self.plan_code,
            "plan_name":    self.plan_name,
            "buy_order":    self.buy_order,
            "amount_clp":   self.amount_clp,
            "card_type":    self.card_type,
            "card_last_four": self.card_last_four,
            "status":       self.status,
            "created_at":   self.created_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }

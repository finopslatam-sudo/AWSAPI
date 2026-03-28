"""
MP SUBSCRIPTION MODEL
=====================
Registra cada suscripción procesada a través de Mercado Pago (preapproval).

Estados:
- pending    : preapproval creado, esperando que el cliente pague en MP
- active     : MP confirmó el pago (status 'authorized'), esperando activación manual
- activated  : admin creó y activó la cuenta del cliente en el sistema
- cancelled  : suscripción cancelada
- rejected   : pago rechazado
"""

from datetime import datetime
from src.models.database import db


class MPSubscription(db.Model):
    __tablename__ = "mp_subscriptions"

    id                 = db.Column(db.Integer,     primary_key=True)
    email              = db.Column(db.String(320), nullable=False, index=True)
    nombre             = db.Column(db.String(255), nullable=True)
    empresa            = db.Column(db.String(255), nullable=True)
    pais               = db.Column(db.String(100), nullable=True)
    telefono           = db.Column(db.String(50),  nullable=True)
    plan_code          = db.Column(db.String(50),  nullable=False)
    plan_name          = db.Column(db.String(100), nullable=False)
    mp_subscription_id = db.Column(db.String(255), nullable=True, unique=True, index=True)
    status             = db.Column(db.String(50),  nullable=False, default="pending")
    created_at         = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow,
                                   onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "email":      self.email,
            "nombre":     self.nombre,
            "empresa":    self.empresa,
            "pais":       self.pais,
            "plan_code":  self.plan_code,
            "plan_name":  self.plan_name,
            "status":     self.status,
            "created_at": self.created_at.isoformat(),
        }

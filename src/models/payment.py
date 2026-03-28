"""
PAYMENT MODEL
=============
Registra cada suscripción procesada a través de PayPal.

Estados:
- pending_approval : suscripción creada, esperando que el cliente apruebe en PayPal
- active           : PayPal confirmó la activación, esperando que admin active la cuenta
- activated        : admin ya creó y activó la cuenta del cliente
- cancelled        : suscripción cancelada
"""

from datetime import datetime
from src.models.database import db


class Payment(db.Model):
    __tablename__ = "payments"

    id                     = db.Column(db.Integer,     primary_key=True)
    email                  = db.Column(db.String(320), nullable=False, index=True)
    nombre                 = db.Column(db.String(255), nullable=True)
    empresa                = db.Column(db.String(255), nullable=True)
    pais                   = db.Column(db.String(100), nullable=True)
    telefono               = db.Column(db.String(50),  nullable=True)
    plan_code              = db.Column(db.String(50),  nullable=False)
    plan_name              = db.Column(db.String(100), nullable=False)
    paypal_subscription_id = db.Column(db.String(255), nullable=True, unique=True, index=True)
    status                 = db.Column(db.String(50),  nullable=False, default="pending_approval")
    created_at             = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow)

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

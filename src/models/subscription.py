from src.database import db
from datetime import datetime
from enum import Enum

class SubscriptionTier(Enum):
    ASSESSMENT = "assessment"      # $499/mes
    INTELLIGENCE = "intelligence"  # $899/mes

class ClientSubscription(db.Model):
    __tablename__ = 'client_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), unique=True, nullable=False)
    tier = db.Column(db.Enum(SubscriptionTier), nullable=False, default=SubscriptionTier.ASSESSMENT)
    monthly_price = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    stripe_subscription_id = db.Column(db.String(100))
    current_period_start = db.Column(db.DateTime, default=datetime.utcnow)
    current_period_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'tier': self.tier.value,
            'monthly_price': float(self.monthly_price),
            'is_active': self.is_active,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None
        }
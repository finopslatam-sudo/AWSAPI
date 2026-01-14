from src.models.database import db
from datetime import datetime
from enum import Enum

class ClientSubscription(db.Model):
    __tablename__ = 'client_subscriptions'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        nullable=False
    )

    plan_id = db.Column(
        db.Integer,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
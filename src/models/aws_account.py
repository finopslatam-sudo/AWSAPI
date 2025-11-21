from src.database import db
from datetime import datetime

class AWSAccount(db.Model):
    __tablename__ = 'aws_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    account_id = db.Column(db.String(12), nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    role_arn = db.Column(db.String(255), nullable=False)
    external_id = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'account_name': self.account_name,
            'is_active': self.is_active,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'created_at': self.created_at.isoformat()
        }
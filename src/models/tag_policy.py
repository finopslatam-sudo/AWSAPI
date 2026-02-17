from src.models.database import db
from datetime import datetime


class TagPolicy(db.Model):
    __tablename__ = "tag_policies"

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    tag_key = db.Column(db.String(100), nullable=False)

    is_required = db.Column(db.Boolean, default=True)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

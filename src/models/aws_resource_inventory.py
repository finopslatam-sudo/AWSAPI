from src.models.database import db


class AWSResourceInventory(db.Model):

    __tablename__ = "aws_resource_inventory"

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    aws_account_id = db.Column(
        db.Integer,
        db.ForeignKey("aws_accounts.id"),
        nullable=False
    )

    resource_id = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)

    region = db.Column(db.String(50))
    state = db.Column(db.String(50))

    tags = db.Column(db.JSON)
    resource_metadata = db.Column(db.JSON)

    detected_at = db.Column(db.DateTime)
    last_seen_at = db.Column(db.DateTime)

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
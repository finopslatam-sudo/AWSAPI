from src.models.database import db


class RiskSnapshot(db.Model):
    __tablename__ = "risk_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, nullable=False)

    # -------------------------------
    # RISK ENGINE SCORE
    # -------------------------------
    risk_score = db.Column(db.Numeric(5, 2))
    risk_level = db.Column(db.String(20))

    # -------------------------------
    # INVENTORY HEALTH SCORE
    # -------------------------------
    health_score = db.Column(db.Integer)

    # -------------------------------
    # DISTRIBUTION
    # -------------------------------
    total_resources = db.Column(db.Integer)
    total_findings = db.Column(db.Integer)

    high_count = db.Column(db.Integer)
    medium_count = db.Column(db.Integer)
    low_count = db.Column(db.Integer)

    governance_percentage = db.Column(db.Numeric(5, 2))
    financial_exposure = db.Column(db.Numeric(10, 2))

    created_at = db.Column(db.DateTime, server_default=db.func.now())
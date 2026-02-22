from src.models.database import db

class RiskSnapshot(db.Model):
    __tablename__ = "risk_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, nullable=False)

    risk_score = db.Column(db.Numeric(5,2))
    risk_level = db.Column(db.String(20))
    governance_percentage = db.Column(db.Numeric(5,2))
    total_resources = db.Column(db.Integer)
    total_findings = db.Column(db.Integer)
    financial_exposure = db.Column(db.Numeric(10,2))

    created_at = db.Column(db.DateTime, server_default=db.func.now())
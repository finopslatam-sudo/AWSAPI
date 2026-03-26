"""
COST EXPLORER CACHE MODEL
=========================
Almacena en BD los resultados de AWS Cost Explorer por cuenta y método.
Evita llamadas repetidas a la API que generan costos en AWS.
"""
from datetime import datetime
from src.models.database import db


class CostExplorerCache(db.Model):
    __tablename__ = "cost_explorer_cache"

    id = db.Column(db.Integer, primary_key=True)

    aws_account_id = db.Column(
        db.Integer,
        db.ForeignKey("aws_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Nombre del método cacheado: '6months' | 'annual' | 'service_breakdown'
    cache_key = db.Column(db.String(30), nullable=False)

    # Resultado serializado como JSON
    data_json = db.Column(db.Text, nullable=False)

    fetched_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint("aws_account_id", "cache_key", name="uq_ce_cache_account_key"),
    )

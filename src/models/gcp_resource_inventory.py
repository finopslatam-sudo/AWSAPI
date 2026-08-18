from src.models.database import db


class GCPResourceInventory(db.Model):
    """Equivalente a AWSResourceInventory/AzureResourceInventory, tabla
    propia (no compartida) para no tocar FKs ya usadas en decenas de
    archivos AWS/Azure."""

    __tablename__ = "gcp_resource_inventory"

    __table_args__ = (
        db.UniqueConstraint(
            "client_id", "resource_id", name="uq_gcp_client_resource"
        ),
        db.Index("idx_gcp_inventory_client_id", "client_id"),
        db.Index("idx_gcp_inventory_client_active", "client_id", "is_active"),
        db.Index("idx_gcp_inventory_type", "client_id", "resource_type"),
        db.Index(
            "idx_gcp_inventory_client_service", "client_id", "service_name",
            postgresql_where=db.text("is_active = true")
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    gcp_account_id = db.Column(
        db.Integer,
        db.ForeignKey("gcp_accounts.id"),
        nullable=False
    )

    service_name = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )  # ComputeEngine, CloudStorage, CloudSQL...

    resource_type = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )  # Instance, Bucket, DatabaseInstance...

    resource_id = db.Column(
        db.String(300),
        nullable=False,
        index=True
    )  # Resource path/self-link de GCP (proyecto/zona/recurso)

    region = db.Column(db.String(50))  # GCP "region" o "zone"
    state = db.Column(db.String(50))

    tags = db.Column(db.JSON)  # GCP "labels", normalizado al mismo campo
    resource_metadata = db.Column(db.JSON)

    detected_at = db.Column(db.DateTime)
    last_seen_at = db.Column(db.DateTime)

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

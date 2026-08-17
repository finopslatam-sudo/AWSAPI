from src.models.database import db


class AzureResourceInventory(db.Model):
    """Equivalente a AWSResourceInventory, tabla propia (no compartida)
    para no tocar la FK aws_account_id ya usada en decenas de archivos AWS."""

    __tablename__ = "azure_resource_inventory"

    __table_args__ = (
        db.UniqueConstraint(
            "client_id", "resource_id", name="uq_azure_client_resource"
        ),
        db.Index("idx_azure_inventory_client_id", "client_id"),
        db.Index("idx_azure_inventory_client_active", "client_id", "is_active"),
        db.Index("idx_azure_inventory_type", "client_id", "resource_type"),
        db.Index(
            "idx_azure_inventory_client_service", "client_id", "service_name",
            postgresql_where=db.text("is_active = true")
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    azure_account_id = db.Column(
        db.Integer,
        db.ForeignKey("azure_accounts.id"),
        nullable=False
    )

    service_name = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )  # VirtualMachines, StorageAccounts, SQLDatabase...

    resource_type = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )  # VirtualMachine, StorageAccount, Database...

    resource_id = db.Column(
        db.String(300),
        nullable=False,
        index=True
    )  # Azure Resource ID (ARM), más largo que un ARN de AWS

    region = db.Column(db.String(50))  # Azure "location" (eastus, westeurope...)
    state = db.Column(db.String(50))

    tags = db.Column(db.JSON)
    resource_metadata = db.Column(db.JSON)

    detected_at = db.Column(db.DateTime)
    last_seen_at = db.Column(db.DateTime)

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

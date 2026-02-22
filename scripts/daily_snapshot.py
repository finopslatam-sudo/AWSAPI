from app import app
from src.models.aws_account import AWSAccount
from src.services.risk_snapshot_service import RiskSnapshotService
from src.models.database import db

def run():

    with app.app_context():

        # Obtener clientes únicos con cuentas activas
        clients = db.session.query(
            AWSAccount.client_id
        ).filter_by(
            is_active=True
        ).distinct().all()

        for (client_id,) in clients:
            print(f"Creating snapshot for client {client_id}")
            RiskSnapshotService.create_snapshot(client_id)

if __name__ == "__main__":
    run()
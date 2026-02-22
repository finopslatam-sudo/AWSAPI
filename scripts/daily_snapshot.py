from app import app
from src.models.client import Client
from src.models.aws_account import AWSAccount
from src.aws.finops_auditor import FinOpsAuditor
from src.services.risk_snapshot_service import RiskSnapshotService

with app.app_context():

    clients = Client.query.filter_by(is_active=True).all()

    for client in clients:

        print(f"\n=== Processing client {client.id} ===")

        accounts = AWSAccount.query.filter_by(
            client_id=client.id,
            is_active=True
        ).all()

        auditor = FinOpsAuditor()

        # 1️⃣ Ejecutar auditoría por cada cuenta AWS
        for account in accounts:
            print(f"Running audit for AWS account {account.id}")
            auditor.run_comprehensive_audit(client.id, account)

        # 2️⃣ Crear snapshot agregado del cliente
        RiskSnapshotService.create_snapshot(client.id)

        print(f"Snapshot created for client {client.id}")
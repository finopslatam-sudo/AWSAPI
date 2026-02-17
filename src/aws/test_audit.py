from app import app
from src.models.aws_account import AWSAccount
from src.aws.finops_auditor import FinOpsAuditor

def run():

    with app.app_context():

        account = AWSAccount.query.filter_by(id=2).first()

        if not account:
            print("No se encontró AWSAccount id=2")
            return

        auditor = FinOpsAuditor()

        result = auditor.run_comprehensive_audit(
            client_id=account.client_id,
            aws_account=account
        )

        print("Resultado auditoría:")
        print(result)


if __name__ == "__main__":
    run()

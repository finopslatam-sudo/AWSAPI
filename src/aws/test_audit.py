from app import app
from src.models.aws_account import AWSAccount
from src.aws.finops_auditor import FinOpsAuditor
from src.aws.sts_service import STSService
import boto3
import os
from datetime import date
from dateutil.relativedelta import relativedelta


print("FINOPS_AWS_ACCESS_KEY_ID:", os.getenv("FINOPS_AWS_ACCESS_KEY_ID"))
print("FINOPS_AWS_SECRET_ACCESS_KEY:", os.getenv("FINOPS_AWS_SECRET_ACCESS_KEY"))
print("AWS_DEFAULT_REGION:", os.getenv("AWS_DEFAULT_REGION"))
print("-----")


def test_cost_explorer(account):

    print("🔎 Probando STS AssumeRole...")

    creds = STSService.assume_role(
        role_arn=account.role_arn,
        external_id=account.external_id
    )

    print("✅ STS exitoso")

    ce = boto3.client(
        "ce",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name="us-east-1"  # Cost Explorer solo funciona aquí
    )

    print("📊 Consultando Cost Explorer...")

    end = date.today().replace(day=1)
    start = end - relativedelta(months=1)

    response = ce.get_cost_and_usage(
        TimePeriod={
            "Start": start.isoformat(),
            "End": end.isoformat()
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"]
    )

    print("✅ Cost Explorer Response:")
    print(response)


def run():

    with app.app_context():

        account = AWSAccount.query.filter_by(id=2).first()

        if not account:
            print("❌ No se encontró AWSAccount id=2")
            return

        print("🚀 Ejecutando auditoría FinOps...")

        auditor = FinOpsAuditor()

        result = auditor.run_comprehensive_audit(
            client_id=account.client_id,
            aws_account=account
        )

        print("Resultado auditoría:")
        print(result)

        print("\n==============================\n")

        test_cost_explorer(account)


if __name__ == "__main__":
    run()

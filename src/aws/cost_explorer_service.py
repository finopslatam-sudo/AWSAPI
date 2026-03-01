import boto3
from datetime import date
from dateutil.relativedelta import relativedelta
from src.aws.sts_service import STSService
from datetime import timedelta


class CostExplorerService:

    def __init__(self, aws_account):
        creds = STSService.assume_role(
            role_arn=aws_account.role_arn,
            external_id=aws_account.external_id
        )

        self.client = boto3.client(
            "ce",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name="us-east-1"
        )

    def get_last_6_months_cost(self):

        end = date.today()
        start = end - relativedelta(months=6)

        response = self.client.get_cost_and_usage(
            TimePeriod={
                "Start": start.replace(day=1).isoformat(),
                "End": end.isoformat()
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"]
        )

        results = []

        for r in response["ResultsByTime"]:

            amount = float(r["Total"]["UnblendedCost"]["Amount"])

            # Normalización AWS floating noise
            if abs(amount) < 0.01:
                amount = 0.0

            results.append({
                "month": r["TimePeriod"]["Start"][:7],
                "amount": amount
            })

        return results

    def get_service_breakdown_current_month(self):

        today = date.today()

        # AWS requiere End exclusivo → usamos mañana
        start = today.replace(day=1)
        end = today + timedelta(days=1)

        # Protección adicional (enterprise safe)
        if start >= end:
            # fallback mínimo válido (evita crash en día 1)
            end = start + timedelta(days=1)

        response = self.client.get_cost_and_usage(
            TimePeriod={
                "Start": start.isoformat(),
                "End": end.isoformat()
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{
                "Type": "DIMENSION",
                "Key": "SERVICE"
            }]
        )

        breakdown = []

        if response.get("ResultsByTime"):
            groups = response["ResultsByTime"][0].get("Groups", [])

            for group in groups:
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])

                if abs(amount) < 0.01:
                    amount = 0.0

                breakdown.append({
                    "service": group["Keys"][0],
                    "amount": amount
                })

        return breakdown
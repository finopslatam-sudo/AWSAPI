import boto3
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class CostExplorerService:

    def __init__(self, aws_credentials):
        self.client = boto3.client(
            "ce",
            aws_access_key_id=aws_credentials.access_key,
            aws_secret_access_key=aws_credentials.secret_key,
            region_name="us-east-1"  # Cost Explorer solo funciona en us-east-1
        )

    def get_last_6_months_cost(self):

        end = date.today().replace(day=1)
        start = end - relativedelta(months=6)

        response = self.client.get_cost_and_usage(
            TimePeriod={
                "Start": start.isoformat(),
                "End": end.isoformat()
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"]
        )

        results = []

        for r in response["ResultsByTime"]:
            results.append({
                "month": r["TimePeriod"]["Start"][:7],
                "amount": float(r["Total"]["UnblendedCost"]["Amount"])
            })

        return results

    def get_service_breakdown_current_month(self):

        start = date.today().replace(day=1)
        end = date.today()

        response = self.client.get_cost_and_usage(
            TimePeriod={
                "Start": start.isoformat(),
                "End": end.isoformat()
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[
                {
                    "Type": "DIMENSION",
                    "Key": "SERVICE"
                }
            ]
        )

        breakdown = []

        for group in response["ResultsByTime"][0]["Groups"]:
            breakdown.append({
                "service": group["Keys"][0],
                "amount": float(group["Metrics"]["UnblendedCost"]["Amount"])
            })

        return breakdown

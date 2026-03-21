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

    def get_annual_costs(self):

        today = date.today()
        current_year = today.year
        prev_year = current_year - 1

        # AWS CE limita el historial a 14 meses por defecto.
        # Usamos 13 meses como límite seguro para evitar ValidationException.
        safe_lookback = (today - relativedelta(months=13)).replace(day=1)

        prev_year_start = max(date(prev_year, 1, 1), safe_lookback)
        prev_year_end   = date(current_year, 1, 1)   # exclusive
        curr_year_start = date(current_year, 1, 1)
        curr_year_end   = today + timedelta(days=1)   # exclusive

        previous_year_cost = 0.0
        current_year_ytd   = 0.0

        # --- Año anterior (puede ser parcial si safe_lookback > Jan 1) ---
        if prev_year_start < prev_year_end:
            try:
                response = self.client.get_cost_and_usage(
                    TimePeriod={
                        "Start": prev_year_start.isoformat(),
                        "End": prev_year_end.isoformat()
                    },
                    Granularity="MONTHLY",
                    Metrics=["UnblendedCost"]
                )
                for r in response.get("ResultsByTime", []):
                    amount = float(r["Total"]["UnblendedCost"]["Amount"])
                    if abs(amount) >= 0.01:
                        previous_year_cost += amount
            except Exception:
                pass

        # --- Año actual YTD (siempre dentro del límite) ---
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    "Start": curr_year_start.isoformat(),
                    "End": curr_year_end.isoformat()
                },
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"]
            )
            for r in response.get("ResultsByTime", []):
                amount = float(r["Total"]["UnblendedCost"]["Amount"])
                if abs(amount) >= 0.01:
                    current_year_ytd += amount
        except Exception:
            pass

        return {
            "previous_year_cost": round(previous_year_cost, 2),
            "current_year_ytd": round(current_year_ytd, 2),
        }

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
"""
ANOMALY MONITOR SERVICE
=======================

Gestiona monitores de AWS Cost Anomaly Detection.

Un monitor se crea automáticamente al conectar cada cuenta AWS.
El motor de alertas lo consulta para obtener anomalías detectadas
por el ML nativo de AWS (más preciso que cálculo manual).

Requiere permiso: ce:CreateAnomalyMonitor, ce:GetAnomalies
"""

import boto3
from datetime import date, timedelta
from botocore.exceptions import ClientError

from src.aws.sts_service import STSService


class AnomalyMonitorService:

    # =====================================================
    # CREAR MONITOR (llamado al conectar cuenta)
    # Recibe una sesión boto3 ya autenticada
    # =====================================================

    @staticmethod
    def create_from_session(session, account_id: str) -> str | None:
        """
        Crea un Anomaly Monitor DIMENSIONAL por servicio
        en la cuenta AWS del cliente.
        Retorna el MonitorArn o None si el rol no tiene permisos.
        """
        try:
            ce = session.client("ce", region_name="us-east-1")
            response = ce.create_anomaly_monitor(
                AnomalyMonitor={
                    "MonitorName": f"FinOpsLatam-{account_id}",
                    "MonitorType": "DIMENSIONAL",
                    "MonitorDimension": "SERVICE",
                }
            )
            arn = response["MonitorArn"]
            print(f"[AnomalyMonitor] Monitor creado para {account_id}: {arn}")
            return arn
        except ClientError as e:
            # No bloquear la conexión si falla — el monitor es opcional
            print(f"[AnomalyMonitor] No se pudo crear monitor para {account_id}: {e}")
            return None

    # =====================================================
    # OBTENER ANOMALÍAS (llamado por el motor de alertas)
    # Crea sesión STS internamente desde la cuenta
    # =====================================================

    @staticmethod
    def get_anomalies(account, min_impact_usd: float = 10.0) -> list:
        """
        Consulta anomalías detectadas por AWS ML en los últimos 90 días.

        Parámetros:
        - account: instancia de AWSAccount con role_arn, external_id y anomaly_monitor_arn
        - min_impact_usd: impacto mínimo en USD para incluir la anomalía

        Retorna lista de dicts con: cuenta, impacto, servicios, fecha_inicio
        """
        if not account.anomaly_monitor_arn:
            return []

        try:
            creds = STSService.assume_role(account.role_arn, account.external_id)
            session = boto3.Session(
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
            )
            ce = session.client("ce", region_name="us-east-1")

            today = date.today().isoformat()
            start = (date.today() - timedelta(days=90)).isoformat()

            response = ce.get_anomalies(
                MonitorArn=account.anomaly_monitor_arn,
                DateInterval={"StartDate": start, "EndDate": today},
                TotalImpact={
                    "NumericOperator": "GREATER_THAN",
                    "StartValue": min_impact_usd,
                },
                MaxResults=10,
            )

            anomalies = []
            for a in response.get("Anomalies", []):
                impact = a.get("Impact", {})
                root_causes = a.get("RootCauses", [])
                services = [rc.get("Service", "") for rc in root_causes[:3] if rc.get("Service")]
                anomalies.append({
                    "cuenta": account.account_name,
                    "impacto_usd": round(impact.get("TotalImpact", 0), 2),
                    "gasto_esperado_usd": round(impact.get("TotalExpectedSpend", 0), 2),
                    "servicios": services,
                    "fecha_inicio": a.get("AnomalyStartDate", ""),
                    "fecha_fin": a.get("AnomalyEndDate", "en curso"),
                })
            return anomalies

        except ClientError as e:
            print(f"[AnomalyMonitor] Error consultando anomalías cuenta {account.account_id}: {e}")
            return []
        except Exception as e:
            print(f"[AnomalyMonitor] Error inesperado cuenta {account.account_id}: {e}")
            return []

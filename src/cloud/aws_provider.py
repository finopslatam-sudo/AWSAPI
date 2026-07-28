"""Adaptador AWS de CloudProvider — envuelve AWSConnector sin reescribir
su lógica (cero cambio de comportamiento)."""

from src.aws.connector import AWSConnector
from src.cloud.base import CloudProvider


class AWSCloudProvider(CloudProvider):
    def __init__(self, role_arn: str, external_id: str | None = None):
        self._connector = AWSConnector(role_arn=role_arn, external_id=external_id)

    def assume_role(self) -> None:
        self._connector.assume_role()

    def get_client(self, service_name: str):
        return self._connector.get_client(service_name)

    def get_session(self):
        """Extra específico de AWS (no parte de la interfaz CloudProvider):
        algunos call sites existentes (resolve_account_name, AnomalyMonitorService)
        necesitan el boto3.Session crudo, no solo un cliente puntual."""
        return self._connector.session

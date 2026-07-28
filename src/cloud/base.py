"""
CLOUD PROVIDER — groundwork de abstracción multi-cloud
=======================================================
Interfaz mínima, basada solo en lo que hoy se usa realmente en el
código (assume_role + get_client vía AWSConnector/STSService). AWS es
la única implementación (aws_provider.AWSCloudProvider); Azure/GCP
quedan explícitamente fuera de esta pasada — ver Fase 3.

El resto de src/aws/* (motores de findings, scanners, cost explorer)
se deja intacto a propósito, llamando a boto3/STSService directamente:
esta interfaz solo se conecta en un punto de entrada (ver
services/aws_connection_service.py), no se migran los ~16 archivos
restantes en esta pasada.
"""

from abc import ABC, abstractmethod
from typing import Any


class CloudProvider(ABC):

    @abstractmethod
    def assume_role(self) -> None:
        """Establece las credenciales para la cuenta de este provider."""
        ...

    @abstractmethod
    def get_client(self, service_name: str) -> Any:
        """Devuelve un cliente SDK nativo del provider para el servicio
        lógico dado (ej. 'ce', 'ec2', 'sts' en AWS)."""
        ...

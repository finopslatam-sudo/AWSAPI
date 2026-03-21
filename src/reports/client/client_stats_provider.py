"""
CLIENT STATS PROVIDER
=====================

Provee métricas visibles únicamente para un cliente.

IMPORTANTE:
- Nunca expone métricas globales
- Nunca incluye datos de otros clientes
- No maneja autenticación (eso vive en routes)
"""

from src.services.client_stats_service import (
    get_users_by_client,
    get_active_services_by_client,
    get_client_plan,
)
from src.services.client_findings_service import ClientFindingsService
from src.models.aws_account import AWSAccount


def get_client_stats(client_id: int) -> dict:
    """
    Datos visibles SOLO para el cliente.
    Nunca incluir métricas globales.
    """

    findings_summary = ClientFindingsService.get_stats(client_id)
    findings_list = ClientFindingsService.list_findings(
        client_id=client_id,
        page=1,
        per_page=200,
        status=None,
        severity=None,
        finding_type=None,
        service=None,
        region=None,
        search=None,
        sort_by="created_at",
        sort_order="desc"
    ).get("data", [])

    account_count = AWSAccount.query.filter_by(
        client_id=client_id, is_active=True
    ).count()

    return {
        "client_id": client_id,
        "user_count": get_users_by_client(client_id),
        "account_count": account_count,
        "active_services": get_active_services_by_client(client_id),
        "plan": get_client_plan(client_id),
        "findings_summary": findings_summary,
        "findings": findings_list,
    }

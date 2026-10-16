"""
CLIENT CLOUD ROUTES
===================
Endpoint unificado para consultar el estado de configuración de todas
las nubes (AWS, Azure, GCP) para un cliente, sus cuentas/suscripciones
y límites asociados.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from src.auth.decorators import require_client_user_role
from src.models.aws_account import AWSAccount
from src.models.azure_account import AzureAccount
from src.models.gcp_account import GCPAccount
from src.auth.plan_permissions import get_plan_limit

client_cloud_bp = Blueprint(
    "client_cloud",
    __name__,
    url_prefix="/api/client/cloud"
)


@client_cloud_bp.route("/status", methods=["GET"])
@jwt_required()
@require_client_user_role()
def get_cloud_status(user):
    """
    Devuelve el estado de conexión de AWS, Azure y GCP para el cliente autenticado.
    Permite al frontend mostrar de un vistazo qué nubes están configuradas y filtrar entre ellas.
    """
    client_id = user.client_id

    # 1. AWS Accounts
    aws_accounts = AWSAccount.query.filter_by(
        client_id=client_id,
        is_active=True
    ).all()
    aws_limit = get_plan_limit(client_id, "aws_accounts")

    # 2. Azure Accounts (Subscriptions)
    azure_accounts = AzureAccount.query.filter_by(
        client_id=client_id,
        is_active=True
    ).all()
    azure_limit = get_plan_limit(client_id, "azure_accounts")

    # 3. GCP Accounts (Projects)
    gcp_accounts = GCPAccount.query.filter_by(
        client_id=client_id,
        is_active=True
    ).all()
    gcp_limit = get_plan_limit(client_id, "gcp_accounts")

    clouds = {
        "aws": {
            "provider": "aws",
            "name": "AWS",
            "icon": "🟠",
            "account_label": "cuentas",
            "is_configured": len(aws_accounts) > 0,
            "status": "connected" if len(aws_accounts) > 0 else "disconnected",
            "accounts_count": len(aws_accounts),
            "accounts_limit": aws_limit,
            "accounts": [a.to_dict() for a in aws_accounts],
        },
        "azure": {
            "provider": "azure",
            "name": "Azure",
            "icon": "🔷",
            "account_label": "suscripciones",
            "is_configured": len(azure_accounts) > 0,
            "status": "connected" if len(azure_accounts) > 0 else "disconnected",
            "accounts_count": len(azure_accounts),
            "accounts_limit": azure_limit,
            "accounts": [a.to_dict() for a in azure_accounts],
        },
        "gcp": {
            "provider": "gcp",
            "name": "GCP",
            "icon": "🔴",
            "account_label": "proyectos",
            "is_configured": len(gcp_accounts) > 0,
            "status": "connected" if len(gcp_accounts) > 0 else "disconnected",
            "accounts_count": len(gcp_accounts),
            "accounts_limit": gcp_limit,
            "accounts": [a.to_dict() for a in gcp_accounts],
        },
    }

    configured_providers = [
        p for p, info in clouds.items() if info["is_configured"]
    ]

    return jsonify({
        "status": "ok",
        "clouds": clouds,
        "configured_providers": configured_providers,
        "total_configured": len(configured_providers),
    }), 200


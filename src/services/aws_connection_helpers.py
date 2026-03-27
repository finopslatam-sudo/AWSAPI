"""
AWS Connection Helpers
======================
Funciones de validación y construcción de ARNs/URLs para conexión AWS.
Sin dependencias de negocio ni base de datos.
"""

import os
import re

from botocore.exceptions import ClientError, BotoCoreError


def resolve_account_name(session, account_id: str) -> str:
    """
    Resolves the AWS account display name.
    Priority: 1) AWS Organizations, 2) IAM Alias, 3) Account ID fallback.
    """
    try:
        org = session.client("organizations")
        response = org.describe_account(AccountId=account_id)
        name = response["Account"]["Name"]
        if name:
            return name
    except (ClientError, BotoCoreError) as e:
        print("Organizations lookup skipped:", str(e))

    try:
        iam = session.client("iam")
        response = iam.list_account_aliases()
        aliases = response.get("AccountAliases", [])
        if aliases:
            return aliases[0]
    except (ClientError, BotoCoreError) as e:
        print("IAM alias lookup skipped:", str(e))

    return account_id


def build_cloudformation_url(external_id: str) -> str:
    finops_account_id = os.getenv("FINOPS_AWS_ACCOUNT_ID")
    if not finops_account_id:
        raise RuntimeError("FINOPS_AWS_ACCOUNT_ID environment variable not set")

    template_url = "https://api.finopslatam.com/api/client/aws/template"
    return (
        "https://console.aws.amazon.com/cloudformation/home"
        "?region=us-east-1#/stacks/create/review"
        f"?templateURL={template_url}"
        f"&stackName=FinOpsLatamStack"
        f"&param_ExternalId={external_id}"
        f"&param_FinOpsAccountId={finops_account_id}"
    )


def validate_role_arn(role_arn: str):
    pattern = r"^arn:aws:iam::\d{12}:role\/.+$"
    if not re.match(pattern, role_arn):
        raise ValueError("Invalid AWS Role ARN")


def validate_account_id(account_id: str):
    pattern = r"^\d{12}$"
    if not re.match(pattern, account_id):
        raise ValueError("Invalid AWS Account ID")


def build_role_arn(account_id: str) -> str:
    return f"arn:aws:iam::{account_id}:role/FinOpsLatam-Audit-Role"

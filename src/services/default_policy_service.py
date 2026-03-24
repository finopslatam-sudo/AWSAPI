"""
DEFAULT POLICY SERVICE
======================

Crea políticas de alerta por defecto al conectar una cuenta AWS.

Regla de negocio:
- Solo aplica a clientes con plan FINOPS_FOUNDATION
- Se crea una política "anomaly-spike" por cuenta conectada
- Usa el email del usuario owner del cliente
- No bloquea la conexión si falla
- Idempotente: no crea duplicados si ya existe la política
"""

from src.models.alert_policy import AlertPolicy
from src.models.user import User
from src.models.database import db
from src.auth.plan_permissions import get_client_plan


def create_default_anomaly_policy(client_id: int, aws_account) -> bool:
    """
    Crea la política anomaly-spike por defecto para clientes Foundation.

    Parámetros:
    - client_id: ID del cliente
    - aws_account: instancia de AWSAccount ya guardada en BD

    Retorna True si se creó, False si no aplica o ya existía.
    """

    # Solo aplica a plan Enterprise
    plan = get_client_plan(client_id)
    if plan != "enterprise":
        return False

    # Idempotente: no crear si ya existe para esta cuenta
    existing = AlertPolicy.query.filter_by(
        client_id=client_id,
        aws_account_id=aws_account.id,
        policy_id="anomaly-spike",
    ).first()

    if existing:
        return False

    # Obtener email del owner del cliente
    owner = User.query.filter_by(
        client_id=client_id,
        client_role="owner",
        is_active=True,
    ).first()

    if not owner or not owner.email:
        print(f"[DefaultPolicy] No se encontró owner activo para client_id={client_id}")
        return False

    policy = AlertPolicy(
        client_id=client_id,
        aws_account_id=aws_account.id,
        policy_id="anomaly-spike",
        title="Anomalía de gasto detectada",
        channel="email",
        email=owner.email,
        threshold=50.0,
        threshold_type="USD",
        period="daily",
    )

    try:
        db.session.add(policy)
        db.session.commit()
        print(
            f"[DefaultPolicy] Política anomaly-spike creada para "
            f"client_id={client_id}, cuenta={aws_account.account_id}, "
            f"email={owner.email}"
        )
        return True
    except Exception as e:
        db.session.rollback()
        print(f"[DefaultPolicy] Error creando política por defecto: {e}")
        return False

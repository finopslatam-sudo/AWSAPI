from typing import Optional

from src.models import db, AlertPolicy, AWSAccount


class AlertPolicyService:

    @staticmethod
    def list_policies(client_id: int):
        policies = AlertPolicy.query.filter_by(client_id=client_id).order_by(AlertPolicy.created_at.desc()).all()
        return [p.to_dict() for p in policies]

    @staticmethod
    def create_policy(
        *,
        client_id: int,
        policy_id: str,
        title: str,
        channel: str,
        email: Optional[str],
        threshold: Optional[float],
        threshold_type: Optional[str],
        period: Optional[str],
        aws_account_id: Optional[int] = None,
    ):

        # validate channel
        allowed_channels = {"email", "slack", "teams"}
        if channel not in allowed_channels:
            raise ValueError("Invalid channel")

        # validate account ownership
        if aws_account_id:
            account = AWSAccount.query.filter_by(id=aws_account_id, client_id=client_id).first()
            if not account:
                raise ValueError("AWS account not found for client")

        policy = AlertPolicy(
            client_id=client_id,
            aws_account_id=aws_account_id,
            policy_id=policy_id,
            title=title,
            channel=channel,
            email=email,
            threshold=threshold,
            threshold_type=threshold_type,
            period=period,
        )

        db.session.add(policy)
        db.session.commit()

        return policy.to_dict()


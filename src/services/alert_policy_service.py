from typing import Optional

from src.models import db, AlertPolicy, AWSAccount


class AlertPolicyService:
    @staticmethod
    def _validate_channel(channel: str):
        allowed_channels = {"email", "slack", "teams"}
        if channel not in allowed_channels:
            raise ValueError("Invalid channel")

    @staticmethod
    def _validate_account(client_id: int, aws_account_id: Optional[int]):
        if aws_account_id:
            account = AWSAccount.query.filter_by(id=aws_account_id, client_id=client_id).first()
            if not account:
                raise ValueError("AWS account not found for client")

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
        AlertPolicyService._validate_channel(channel)
        AlertPolicyService._validate_account(client_id, aws_account_id)

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

    @staticmethod
    def update_policy(
        *,
        client_id: int,
        policy_db_id: int,
        policy_id: str,
        title: str,
        channel: str,
        email: Optional[str],
        threshold: Optional[float],
        threshold_type: Optional[str],
        period: Optional[str],
        aws_account_id: Optional[int] = None,
    ):
        policy = AlertPolicy.query.filter_by(id=policy_db_id, client_id=client_id).first()
        if not policy:
            raise ValueError("Alert policy not found")

        AlertPolicyService._validate_channel(channel)
        AlertPolicyService._validate_account(client_id, aws_account_id)

        policy.policy_id = policy_id
        policy.title = title
        policy.channel = channel
        policy.email = email
        policy.threshold = threshold
        policy.threshold_type = threshold_type
        policy.period = period
        policy.aws_account_id = aws_account_id

        db.session.commit()

        return policy.to_dict()

    @staticmethod
    def delete_policy(*, client_id: int, policy_db_id: int):
        policy = AlertPolicy.query.filter_by(id=policy_db_id, client_id=client_id).first()
        if not policy:
            raise ValueError("Alert policy not found")

        db.session.delete(policy)
        db.session.commit()

from .database import db
from .client import Client
from .plan import Plan
from .subscription import ClientSubscription
from .aws_account import AWSAccount
from .user import User
from .alert_policy import AlertPolicy
from .cost_explorer_cache import CostExplorerCache  # noqa: F401 — registra tabla en SQLAlchemy
from .patpass_inscription import PatpassInscription  # noqa: F401 — registra tabla en SQLAlchemy

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User
from src.models.database import db
from src.services.password_service import validate_password_policy

me_bp = Blueprint("me", __name__, url_prefix="/api/me")

from flask import Blueprint, jsonify
from src.services.email_service import send_email

test_smtp_bp = Blueprint("test_smtp", __name__)

@test_smtp_bp.route("/api/test-smtp", methods=["GET"])
def test_smtp():
    send_email(
        "finopslatam@gmail.com",
        "Test SMTP Zoho",
        "Correo de prueba enviado desde producción FinOpsLatam"
    )
    return jsonify({"status": "ok", "message": "Correo enviado"})

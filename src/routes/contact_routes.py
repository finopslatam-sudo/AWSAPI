from flask import Blueprint, request, jsonify
import os
import smtplib
from email.message import EmailMessage

contact_bp = Blueprint("contact", __name__)

@contact_bp.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json()

    required_fields = ["nombre", "empresa", "email", "servicio", "mensaje"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Campo requerido: {field}"}), 400

    try:
        msg = EmailMessage()
        msg["Subject"] = f"Nuevo contacto FinOpsLatam – {data['servicio']}"
        msg["From"] = os.getenv("SMTP_USER")
        msg["To"] = os.getenv("SMTP_USER")  # contacto@finopslatam.com

        msg.set_content(f"""
Nuevo contacto desde FinOpsLatam

Nombre: {data['nombre']}
Empresa: {data['empresa']}
Email: {data['email']}
Teléfono: {data.get('telefono', 'No informado')}
Servicio: {data['servicio']}

Mensaje:
{data['mensaje']}
        """)

        server = smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT")))
        server.starttls()
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        server.send_message(msg)
        server.quit()

        return jsonify({"message": "Mensaje enviado correctamente"}), 200

    except Exception as e:
        print("ERROR CONTACT:", e)
        return jsonify({"error": "Error interno al enviar el mensaje"}), 500

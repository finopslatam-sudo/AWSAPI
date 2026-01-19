from flask import Blueprint, request, jsonify
import os
import smtplib
from email.message import EmailMessage

contact_bp = Blueprint("contact", __name__)

@contact_bp.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "JSON inválido o vacío"}), 400

    required_fields = ["nombre", "empresa", "email", "servicio", "mensaje"]
    missing = [f for f in required_fields if not data.get(f)]

    if missing:
        return jsonify({"error": f"Campos requeridos faltantes: {', '.join(missing)}"}), 400

    # 🔐 Validación SMTP (enterprise)
    smtp_vars = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS"]
    missing_smtp = [v for v in smtp_vars if not os.getenv(v)]

    if missing_smtp:
        print(f"⚠️ SMTP no configurado correctamente: {missing_smtp}")
        return jsonify({"error": "Servicio de correo no disponible"}), 500

    try:
        msg = EmailMessage()
        msg["Subject"] = f"📩 Nuevo contacto FinOpsLatam – {data['servicio']}"
        msg["From"] = f"FinOpsLatam <{os.getenv('SMTP_USER')}>"
        msg["To"] = "contacto@finopslatam.com"
        msg["Reply-To"] = data["email"]

        msg.set_content(
            f"""
Nuevo contacto desde FinOpsLatam

Nombre: {data['nombre']}
Empresa: {data['empresa']}
Email: {data['email']}
Teléfono: {data.get('telefono', 'No informado')}
Servicio de interés: {data['servicio']}

Mensaje:
{data['mensaje']}
            """,
            charset="utf-8"
        )

        with smtplib.SMTP(
            os.getenv("SMTP_HOST"),
            int(os.getenv("SMTP_PORT")),
            timeout=15
        ) as server:
            server.starttls()
            server.login(
                os.getenv("SMTP_USER"),
                os.getenv("SMTP_PASS")
            )
            server.send_message(msg)

        return jsonify({"message": "Mensaje enviado correctamente"}), 200

    except Exception as e:
        print("❌ ERROR CONTACT ROUTE:", str(e))
        return jsonify({"error": "Error interno al enviar el mensaje"}), 500

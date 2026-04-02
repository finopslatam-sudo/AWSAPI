"""
CONTACT ROUTES
==============

Endpoint público para formulario de contacto del sitio FinOpsLatam.

IMPORTANTE:
- No requiere autenticación
- No forma parte del core SaaS
- Delegación completa del envío de correo a email_service
"""

import logging
from flask import Blueprint, request, jsonify

from src.services.email_service import send_email
from src.models.user import User
from src.security.validation import is_valid_email, normalize_email

contact_bp = Blueprint("contact", __name__)
logger = logging.getLogger("contact")


@contact_bp.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "JSON inválido o vacío"}), 400

    required_fields = ["nombre", "empresa", "email", "servicio", "mensaje"]
    missing = [f for f in required_fields if not data.get(f)]

    if missing:
        return jsonify({
            "error": f"Campos requeridos faltantes: {', '.join(missing)}"
        }), 400

    email = normalize_email(str(data.get("email", "")))
    if not is_valid_email(email):
        return jsonify({"error": "Email inválido"}), 400

    nombre = str(data.get("nombre", "")).strip()[:255]
    empresa = str(data.get("empresa", "")).strip()[:255]
    servicio = str(data.get("servicio", "")).strip()[:120]
    telefono = str(data.get("telefono", "No informado")).strip()[:60]
    mensaje = str(data.get("mensaje", "")).strip()[:4000]

    body = f"""
Nuevo contacto desde FinOpsLatam

Nombre: {nombre}
Empresa: {empresa}
Email: {email}
Teléfono: {telefono}
Servicio de interés: {servicio}

Mensaje:
{mensaje}
"""

    sent = send_email(
        to="contacto@finopslatam.com",
        subject=f"📩 Nuevo contacto – {servicio}",
        body=body,
    )

    if not sent:
        logger.warning(
            "No se pudo enviar correo de contacto desde %s",
            email
        )
        return jsonify({
            "error": "Servicio de correo no disponible"
        }), 500

    # Notificar a todos los usuarios globales (staff)
    global_users = User.query.filter(
        User.global_role.isnot(None),
        User.is_active == True,
    ).all()
    notified_emails = {"contacto@finopslatam.com"}
    for staff_user in global_users:
        if staff_user.email not in notified_emails:
            send_email(
                to=staff_user.email,
                subject=f"🔔 Nueva solicitud de consultoría – {empresa}",
                body=body,
            )
            notified_emails.add(staff_user.email)

    logger.info(
        "Contacto recibido desde %s (%s)",
        email,
        empresa,
    )

    return jsonify({
        "message": "Mensaje enviado correctamente"
    }), 200

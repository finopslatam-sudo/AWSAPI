"""
EMAIL SERVICE
=============

Servicio centralizado para envío de correos vía SMTP.

Responsabilidades:
- Enviar correos transaccionales (password reset, eventos admin)
- Manejar conexión SMTP de forma segura
- NO exponer credenciales en logs

Notas:
- En entornos sin SMTP configurado, el envío se omite
- El fallo de envío NO debe romper el flujo principal
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("email")


def send_email(to: str, subject: str, body: str) -> bool:
    """
    Envía un correo electrónico vía SMTP.

    Retorna:
        True  -> correo enviado correctamente
        False -> fallo o SMTP no configurado
    """

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not all([smtp_host, smtp_user, smtp_pass]):
        logger.warning("SMTP no configurado. Envío de correo omitido.")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"Correo enviado correctamente a {to}")
        return True

    except Exception as exc:
        logger.exception("Error enviando correo")
        return False

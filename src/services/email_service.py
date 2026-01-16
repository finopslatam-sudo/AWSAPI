import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger("email")


def send_email(to: str, subject: str, body: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    # 🔍 DEBUG TEMPORAL — VALIDAR CONTEXTO SYSTEMD
    if os.getenv("TEST_SMTP") == "1":
        logger.info("[EMAIL] SMTP activo en contexto systemd")

    logger.info(f"[EMAIL] Intentando enviar correo a {to}")
    logger.info(f"[EMAIL] SMTP_HOST={smtp_host} SMTP_PORT={smtp_port} SMTP_USER={smtp_user}")

    if not all([smtp_host, smtp_user, smtp_pass]):
        logger.error("[EMAIL] Configuración SMTP incompleta")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            logger.info("[EMAIL] Conectando a SMTP…")
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"[EMAIL] Correo enviado correctamente a {to}")

    except Exception as e:
        logger.exception(f"[EMAIL ERROR] Fallo enviando correo a {to}: {e}")


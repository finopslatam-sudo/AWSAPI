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

    logger.info("SMTP CHECK")
    logger.info(f"HOST={smtp_host}")
    logger.info(f"PORT={smtp_port}")
    logger.info(f"USER={smtp_user}")
    logger.info(f"PASS_SET={'YES' if smtp_pass else 'NO'}")

    if not all([smtp_host, smtp_user, smtp_pass]):
        logger.error("Configuración SMTP incompleta")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            logger.info("Conectando a SMTP…")
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"Correo enviado correctamente a {to}")

    except Exception as e:
        logger.exception(f"Fallo enviando correo: {e}")



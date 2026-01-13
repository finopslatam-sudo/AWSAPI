from flask import Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from flask_migrate import Migrate
import secrets
import string
from datetime import datetime
import os
import csv
from io import StringIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib.styles import getSampleStyleSheet


import matplotlib.pyplot as plt
import tempfile

# ===============================
# INIT EXTENSIONS
# ===============================
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

# ===============================
# HELPERS
# ===============================
def generate_temp_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def require_admin(client_id: int) -> bool:
    client = Client.query.get(client_id)
    return bool(client and client.role == "admin")

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(to: str, subject: str, body: str):
    try:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")

        if not all([smtp_host, smtp_user, smtp_pass]):
            raise RuntimeError("Configuración SMTP incompleta")

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

    except Exception as e:
        print(f"[EMAIL ERROR] No se pudo enviar correo a {to}: {e}")

# =====================================================
# 📊 ADMIN — MÉTRICAS REUTILIZABLES (DASHBOARD)
# =====================================================
def get_admin_stats():
    total_users = Client.query.count()
    active_users = Client.query.filter_by(is_active=True).count()
    inactive_users = total_users - active_users

    users_by_plan = (
        db.session.query(
            Plan.name.label("plan"),
            db.func.count(ClientSubscription.id).label("count")
        )
        .join(ClientSubscription, ClientSubscription.plan_id == Plan.id)
        .filter(ClientSubscription.is_active == True)
        .group_by(Plan.name)
        .all()
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "users_by_plan": [
            {"plan": plan, "count": count}
            for plan, count in users_by_plan
        ]
    }

def generate_users_by_plan_chart(stats):
    plans = [p["plan"] for p in stats["users_by_plan"]]
    counts = [p["count"] for p in stats["users_by_plan"]]

    fig, ax = plt.subplots()
    ax.bar(plans, counts)
    ax.set_title("Usuarios por plan")
    ax.set_ylabel("Cantidad")

    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    plt.savefig(temp_file.name)
    plt.close(fig)

    return temp_file.name


# ===============================
# EMAIL HELPERS (SEGURIDAD)
# ===============================
def build_forgot_password_email(nombre, email, temp_password):
    return f"""
Hola {nombre},

Recibimos una solicitud para recuperar tu acceso a FinOpsLatam 🔐

Se ha generado una contraseña temporal para que puedas ingresar:

Usuario: {email}
Contraseña temporal: {temp_password}

👉 Accede aquí:
https://www.finopslatam.com/

⚠️ Al iniciar sesión se te pedirá cambiar esta contraseña por una definitiva.

Si no solicitaste este acceso, ignora este correo.

Saludos,
Equipo FinOpsLatam
"""

def build_password_changed_email(nombre):
    return f"""
Hola {nombre},

Te informamos que la contraseña de tu cuenta en FinOpsLatam fue cambiada correctamente.

Si no realizaste este cambio o detectas algo extraño, contáctanos de inmediato en:
soporte@finopslatam.com

Saludos,
Equipo FinOpsLatam
"""
# ===============================
# EMAIL HELPERS (ADMIN)
# ===============================

def build_account_reactivated_email(nombre):
    return f"""
Hola {nombre},

Tu cuenta en FinOpsLatam ha sido reactivada exitosamente 🎉

Por seguridad, en tu próximo inicio de sesión se te pedirá
actualizar tu contraseña.

👉 Accede aquí:
https://www.finopslatam.com/

Si tienes dudas, escríbenos a:
soporte@finopslatam.com

Saludos,
Equipo FinOpsLatam
"""

# ================================
# EMAIL HELPERS CUENTA DESACTIVADA
# ================================

def build_account_deactivated_email(nombre):
    return f"""
Hola {nombre},

Tu cuenta en FinOpsLatam ha sido desactivada temporalmente 🔒

Si crees que esto es un error o necesitas más información,
puedes contactarnos en:

soporte@finopslatam.com

Saludos,
Equipo FinOpsLatam
"""
# =========================================
# EMAIL HELPERS RESET DE PASSWORD POR ADMIN
# =========================================

def build_admin_reset_password_email(nombre: str, email: str, password: str) -> str:
    return f"""
Hola {nombre},

Un administrador ha restablecido la contraseña de tu cuenta en FinOpsLatam 🔐

Por seguridad, deberás cambiar tu contraseña en tu primer inicio de sesión.

🔐 Datos de acceso
Usuario: {email}
Contraseña temporal: {password}

👉 Accede aquí:
https://www.finopslatam.com/

Si no solicitaste este cambio, contáctanos inmediatamente:
soporte@finopslatam.com

Saludos,
Equipo FinOpsLatam
"""
# =========================================
# EMAIL HELPERS CAMBIO DE PLAN
# =========================================
def build_plan_changed_email(nombre, plan_name):
    return f"""
Hola {nombre},

Te informamos que tu plan en FinOpsLatam ha sido actualizado correctamente.

📦 Nuevo plan activo:
{plan_name}

Los cambios se aplican de inmediato en la plataforma.

👉 Accede aquí:
https://www.finopslatam.com/

Si tienes dudas sobre tu plan o sus beneficios,
escríbenos a:
soporte@finopslatam.com

Saludos,
Equipo FinOpsLatam
"""

# ===============================
# MODELS
# ===============================
class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    contact_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default="client", nullable=False)
    force_password_change = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    password_expires_at = db.Column(db.DateTime, nullable=True)

    # 🔐 ÚNICO LUGAR DONDE EXISTE bcrypt
    def set_password(self, password: str):
        import bcrypt
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        if not password or not self.password_hash:
            return False
        try:
            import bcrypt
            return bcrypt.checkpw(
                password.encode("utf-8"),
                self.password_hash.encode("utf-8")
            )
        except Exception:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
        }

class Plan(db.Model):
    __tablename__ = "plans"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

class ClientSubscription(db.Model):
    __tablename__ = "client_subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

# ===============================
# INIT SYSTEM
# ===============================
def init_auth_system(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("❌ SQLALCHEMY_DATABASE_URI no definida")

    app.config["JWT_SECRET_KEY"] = os.getenv(
        "JWT_SECRET_KEY", "finopslatam-prod-secret"
    )

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

# ===============================
# ROUTES
# ===============================
def create_auth_routes(app):

    # -------- LOGIN (ÚNICO Y DEFINITIVO) --------
    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email y password son obligatorios"}), 400

        result = (
            db.session.query(Client, ClientSubscription, Plan)
            .outerjoin(
                ClientSubscription,
                ClientSubscription.client_id == Client.id
            )
            .outerjoin(
                Plan,
                Plan.id == ClientSubscription.plan_id
            )
            .filter(
                Client.email == email,
                Client.is_active == True
            )
            .first()
        )

        if not result:
            return jsonify({"error": "Credenciales inválidas"}), 401

        client, subscription, plan = result

        if not client.check_password(password):
            return jsonify({"error": "Credenciales inválidas"}), 401
        
        # 🔐 BLOQUEAR CLAVE TEMPORAL VENCIDA
        if client.force_password_change and client.password_expires_at:
            from datetime import datetime
            if datetime.utcnow() > client.password_expires_at:
                return jsonify({
                    "error": "La clave temporal ha expirado. Solicita una nueva."
                }), 401

        # 🔐 CLIENTE: debe tener plan activo
        if client.role == "client":
            if not subscription or not subscription.is_active or not plan:
                return jsonify({
                    "error": "Usuario sin plan activo"
                }), 403

        token = create_access_token(identity=str(client.id))

        response = {
            "access_token": token,
            "user": {
                "id": client.id,
                "email": client.email,
                "company_name": client.company_name,
                "contact_name": client.contact_name,
                "phone": client.phone,
                "role": client.role,
                "is_active": client.is_active,
                "force_password_change": client.force_password_change,
            }
        }

        # 📦 Solo clientes llevan plan
        if client.role == "client":
            response["user"]["plan"] = {
                "id": plan.id,
                "code": plan.code,
                "name": plan.name
            }

        return jsonify(response), 200

    # ---------------------------------------------
    # USUARIO — ACTUALIZAR MI PERFIL (SEGURO)
    # ---------------------------------------------
    @app.route('/api/users/me', methods=['PUT'])
    @jwt_required()
    def update_my_profile():
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}

        user = Client.query.get(user_id)

        if not user:
            return jsonify({
                "error": "Usuario no encontrado"
            }), 404

        # 🔧 SOLO CAMPOS PERMITIDOS
        if 'contact_name' in data:
            user.contact_name = data['contact_name']

        if 'phone' in data:
            user.phone = data['phone']

        db.session.commit()

        return jsonify({
            "message": "Perfil actualizado correctamente",
            "user": {
                "contact_name": user.contact_name,
                "phone": user.phone
            }
        }), 200
    # ---------------------------------------------
    # ADMIN — ACTUALIZAR PLAN DE USUARIO (FIXED)
    # ---------------------------------------------
    @app.route('/api/admin/users/<int:user_id>/plan', methods=['PUT'])
    @jwt_required()
    def admin_update_user_plan(user_id):
        admin_id = int(get_jwt_identity())

        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        data = request.get_json() or {}
        plan_id = data.get("plan_id")

        if not plan_id:
            return jsonify({"error": "plan_id requerido"}), 400

        # ✅ BUSCAR POR ID (NO code)
        plan = Plan.query.filter_by(id=plan_id).first()
        if not plan:
            return jsonify({"error": "Plan no encontrado"}), 404

        # 🔎 Buscar suscripción existente
        subscription = ClientSubscription.query.filter_by(
            client_id=user_id,
            is_active=True
        ).order_by(ClientSubscription.id.desc()).first()

        if subscription:
            # ✅ UPDATE (NO INSERT)
            subscription.plan_id = plan.id
            subscription.is_active = True
        else:
            # ✅ Solo si no existe
            subscription = ClientSubscription(
                client_id=user_id,
                plan_id=plan.id,
                is_active=True
            )
            db.session.add(subscription)

        db.session.commit()

        # 📧 AVISO DE CAMBIO DE PLAN
        try:
            user = Client.query.get(user_id)
            send_email(
                to=user.email,
                subject="Tu plan ha sido actualizado 📦 | FinOpsLatam",
                body=build_plan_changed_email(
                    user.contact_name,
                    plan.name
                )
            )
        except Exception as e:
            app.logger.error(
                f"Error enviando correo cambio plan usuario {user_id}: {e}"
            )

        return jsonify({
            "message": "Plan actualizado correctamente",
            "user_id": user_id,
            "plan": {
                "id": plan.id,
                "code": plan.code,
                "name": plan.name
            }
        }), 200

    # ---------------------------------------------
    # ADMIN — ACTUALIZAR DATOS DE USUARIO / ROL
    # ---------------------------------------------
    @app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
    @jwt_required()
    def admin_update_user(user_id):
        admin_id = int(get_jwt_identity())

        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "Payload vacío"}), 400

        user = Client.query.get_or_404(user_id)

        # 🔧 Guardar estado anterior
        previous_state = user.is_active

        # 🔧 Datos básicos
        user.company_name = data.get("company_name", user.company_name)
        user.contact_name = data.get("contact_name", user.contact_name)
        user.phone = data.get("phone", user.phone)

        # ✅ EMAIL
        if "email" in data:
            user.email = data["email"]

        # ✅ Estado activo / inactivo (DETECCIÓN DE TRANSICIÓN)
        if "is_active" in data:
            new_state = data["is_active"]
            user.is_active = new_state

            # 🔴 ACTIVO → INACTIVO → correo de desactivación
            if previous_state is True and new_state is False:
                try:
                    send_email(
                        to=user.email,
                        subject="Tu cuenta ha sido desactivada 🔒 | FinOpsLatam",
                        body=build_account_deactivated_email(user.contact_name)
                    )
                except Exception as e:
                    app.logger.error(
                        f"Error enviando correo desactivación usuario {user.id}: {e}"
                    )

            # 🟢 INACTIVO → ACTIVO → forzar cambio + correo
            if previous_state is False and new_state is True:
                user.force_password_change = True
                try:
                    send_email(
                        to=user.email,
                        subject="Tu cuenta ha sido reactivada 🔓 | FinOpsLatam",
                        body=build_account_reactivated_email(user.contact_name)
                    )
                except Exception as e:
                    app.logger.error(
                        f"Error enviando correo reactivación usuario {user.id}: {e}"
                    )

        # 🔐 Evitar que admin se quite su propio rol
        if "role" in data:
            if user.id == admin_id:
                return jsonify({"error": "No puedes modificar tu propio rol"}), 400
            user.role = data["role"]

        # 💾 Persistir cambios
        db.session.commit()

        # 🧠 Logging
        app.logger.info(
            f"Admin {admin_id} actualizó usuario {user_id} | "
            f"estado: {previous_state} -> {user.is_active}"
        )

        return jsonify({
            "message": "Usuario actualizado correctamente",
            "user_id": user.id
        }), 200

    # ---------------------------------------------
    # CAMBIO DE PASSWORD OBLIGATORIO
    # (primer login o reactivación de cuenta)
    # ---------------------------------------------
    @app.route('/api/auth/change-password', methods=['POST'])
    @jwt_required()
    def change_password():
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}

        current_password = data.get("current_password")
        password = data.get("password")
        confirm = data.get("confirm_password")

        # 🔴 Validaciones básicas
        if not current_password or not password or not confirm:
            return jsonify({"error": "Todos los campos son obligatorios"}), 400

        if password != confirm:
            return jsonify({"error": "Las contraseñas no coinciden"}), 400

        if len(password) < 8 or len(password) > 12:
            return jsonify({
                "error": "La contraseña debe tener entre 8 y 12 caracteres"
            }), 400

        user = Client.query.get_or_404(user_id)

        # 🔐 VALIDAR CLAVE ACTUAL
        if not user.check_password(current_password):
            return jsonify({"error": "Clave actual incorrecta"}), 400

        # 🚫 BLOQUEAR REUTILIZACIÓN DE CONTRASEÑA
        # (bcrypt-safe)
        if user.check_password(password):
            return jsonify({
                "error": "La nueva contraseña no puede ser igual a la actual"
            }), 400

        user.set_password(password)
        user.force_password_change = False
        user.password_expires_at = None

        db.session.commit()

        # 📧 AVISO DE CAMBIO DE CONTRASEÑA
        send_email(
            to=user.email,
            subject="Tu contraseña ha sido actualizada �� | FinOpsLatam",
            body=build_password_changed_email(user.contact_name)
        )

        return jsonify({
            "message": "Contraseña actualizada correctamente"
        }), 200

    # ---------------------------------------------
    # AUTH — RECUPERAR CONTRASEÑA (USUARIO)
    # ---------------------------------------------
    @app.route("/api/auth/forgot-password", methods=["POST"])
    def forgot_password():
        data = request.get_json() or {}
        email = data.get("email")

        # ⚠️ Respuesta SIEMPRE genérica
        if not email:
            return jsonify({
                "message": "Si el correo existe, recibirás instrucciones"
            }), 200

        user = Client.query.filter_by(email=email).first()

        # ⚠️ NO revelar si existe o no
        if not user or not user.is_active:
            return jsonify({
                "message": "Si el correo existe, recibirás instrucciones"
            }), 200

        # 🔐 Generar contraseña temporal
        temp_password = generate_temp_password()

        # 🔐 Guardar password + forzar cambio
        from datetime import datetime, timedelta

        user.set_password(temp_password)
        user.force_password_change = True
        user.password_expires_at = datetime.utcnow() + timedelta(minutes=30)

        db.session.commit()

        # �� Enviar correo
        try:
            send_email(
                to=user.email,
                subject="Recuperación de acceso | FinOpsLatam",
                body=build_forgot_password_email(
                    user.contact_name,
                    user.email,
                    temp_password
                )
            )
        except Exception as e:
            app.logger.error(
                f"Error enviando email recuperación usuario {user.id}: {e}"
            )

        return jsonify({
            "message": "Si el correo existe, recibirás instrucciones"
        }), 200

    # ---------------------------------------------
    # ADMIN — ELIMINAR USUARIO (SOFT DELETE)
    # ---------------------------------------------
    @app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
    @jwt_required()
    def admin_delete_user(user_id):
        admin_id = int(get_jwt_identity())

        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        user = Client.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # 🔐 Evitar que el admin se elimine a sí mismo
        if user.id == admin_id:
            return jsonify({
                "error": "No puedes eliminar tu propio usuario"
            }), 400

        # ✅ Soft delete
        user.is_active = False
        db.session.commit()

        try:
            send_email(
                to=user.email,
                subject="Tu cuenta ha sido desactivada 🔒 | FinOpsLatam",
                body=build_account_deactivated_email(user.contact_name)
            )
        except Exception as e:
            app.logger.error(
                f"Error enviando correo desactivación usuario {user.id}: {e}"
            )


        # 🧠 Logging
        app.logger.info(
            f"Admin {admin_id} desactivó usuario {user_id}"
        )

        return jsonify({
            "message": "Usuario desactivado correctamente",
            "user_id": user.id
        }), 200

    # ---------------------------------------------
    # ADMIN — RESET PASSWORD USUARIO (FINAL)
    # ---------------------------------------------
    @app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
    @jwt_required()
    def admin_reset_password(user_id):
        admin_id = int(get_jwt_identity())

        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        if admin_id == user_id:
            return jsonify({
                "error": "No puedes resetear tu propia contraseña"
            }), 400

        data = request.get_json() or {}
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        # -------------------------------
        # VALIDACIONES
        # -------------------------------
        if not password or not confirm_password:
            return jsonify({
                "error": "Password y confirmación son obligatorios"
            }), 400

        if password != confirm_password:
            return jsonify({
                "error": "Las contraseñas no coinciden"
            }), 400

        if len(password) < 8:
            return jsonify({
                "error": "La contraseña debe tener al menos 8 caracteres"
            }), 400

        # -------------------------------
        # USUARIO
        # -------------------------------
        user = Client.query.get_or_404(user_id)

        # -------------------------------
        # PASSWORD (ÚNICO LUGAR)
        # -------------------------------
        from datetime import datetime, timedelta

        user.set_password(password)
        user.force_password_change = True
        user.password_expires_at = datetime.utcnow() + timedelta(minutes=30)
        user.is_active = True

        # -------------------------------
        # 📧 EMAIL CON CREDENCIALES
        # -------------------------------
        try:
            send_email(
                to=user.email,
                subject="Tu contraseña fue restablecida | FinOpsLatam",
                body=build_admin_reset_password_email(
                    user.contact_name,
                    user.email,
                    password  
                )
            )
        except Exception as e:
            app.logger.error(
                f"Error enviando correo reset password usuario {user.id}: {e}"
            )

        app.logger.info(
            f"[ADMIN] {admin_id} reseteó password del usuario {user_id}"
        )

        return jsonify({
            "message": "Contraseña restablecida correctamente"
        }), 200

    # ---------------------------------------------
    # ADMIN — LISTAR USUARIOS (CON PLAN)
    # ---------------------------------------------
    @app.route('/api/admin/users', methods=['GET'])
    @jwt_required()
    def admin_list_users():
        admin_id = int(get_jwt_identity())

        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        users = (
            db.session.query(Client, ClientSubscription, Plan)
            .outerjoin(
                ClientSubscription,
                (Client.id == ClientSubscription.client_id)
                & (ClientSubscription.is_active == True)
            )
            .outerjoin(
                Plan,
                ClientSubscription.plan_id == Plan.id
            )
            .all()
        )

        return jsonify({
            "users": [
                {
                    "id": client.id,
                    "email": client.email,
                    "company_name": client.company_name,
                    "contact_name": client.contact_name,
                    "phone": client.phone,
                    "role": client.role,
                    "is_active": client.is_active,
                    "plan": {
                        "id": plan.id,
                        "code": plan.code,
                        "name": plan.name,
                    } if plan else None
                }
                for client, subscription, plan in users
            ]
        }), 200


    # ---------------------------------------------
    # ADMIN — ESTADÍSTICAS GENERALES (DASHBOARD)
    # ---------------------------------------------
    @app.route('/api/admin/stats', methods=['GET'])
    @jwt_required()
    def admin_stats():
        admin_id = int(get_jwt_identity())

        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        return jsonify(get_admin_stats()), 200

   

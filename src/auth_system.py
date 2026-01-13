from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from flask_migrate import Migrate
import secrets
import string
from datetime import datetime
import os

# Configuración de database separada
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


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
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

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

            # Asignar plan por defecto (Cloud Assessment)
            default_plan = Plan.query.filter_by(code='cloud_assessment').first()

            if not default_plan:
                return jsonify({"error": "Plan por defecto no encontrado"}), 500

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
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        try:
            data = request.get_json()
            
            if not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email y password son requeridos'}), 400
            
            client = Client.query.filter_by(email=data['email']).first()
            
            if not client or not client.check_password(data['password']):
                return jsonify({'error': 'Credenciales inválidas'}), 401
            
            subscription = ClientSubscription.query.filter_by(
                client_id=client.id
            ).first()
            
            access_token = create_access_token(identity=str(client.id))
            
            return jsonify({
                "message": "Si el correo existe, recibirás instrucciones"
            }), 200
            
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

        subscription = (
            ClientSubscription.query
            .filter_by(client_id=client_id, is_active=True)
            .first()
        )

        if not subscription:
            return jsonify({"error": "No tienes un plan activo"}), 404

        plan = Plan.query.get(subscription.plan_id)

        features = [f.code for f in plan.features]

        return jsonify({
            "message": "Contraseña restablecida correctamente"
        }), 200

    # ---------------------------------------------
    # ADMIN — LISTAR USUARIOS (CON PLAN)
    # ---------------------------------------------
    @app.route('/api/admin/users', methods=['GET'])
    @jwt_required()
    def get_profile():
        try:
            client_id = get_jwt_identity()
            client = Client.query.get(client_id)
            
            if not client:
                return jsonify({'error': 'Cliente no encontrado'}), 404
            
            subscription = ClientSubscription.query.filter_by(
                client_id=client_id
            ).first()
            
            return jsonify({
                'client': client.to_dict(),
                'subscription': subscription.to_dict() if subscription else None
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app

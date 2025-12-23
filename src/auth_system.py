from flask import jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from flask_migrate import Migrate
from datetime import datetime
import bcrypt
import os

# ===============================
# INIT EXTENSIONS
# ===============================
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


# ===============================
# HELPERS
# ===============================
def require_admin(client_id: int) -> bool:
    client = Client.query.get(client_id)
    return bool(client and client.role == "admin")


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
    role = db.Column(db.String(20), nullable=False, default="client")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            self.password_hash.encode("utf-8")
        )

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company_name,
            "email": self.email,
            "contact_name": self.contact_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "role": self.role,
            "created_at": self.created_at.isoformat()
        }


class Plan(db.Model):
    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    monthly_price = db.Column(db.Numeric(10, 2))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    features = db.relationship(
        "Feature",
        secondary="plan_features",
        backref="plans"
    )


class Feature(db.Model):
    __tablename__ = "features"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)


class PlanFeature(db.Model):
    __tablename__ = "plan_features"

    plan_id = db.Column(
        db.Integer, db.ForeignKey("plans.id"), primary_key=True
    )
    feature_id = db.Column(
        db.Integer, db.ForeignKey("features.id"), primary_key=True
    )


class ClientSubscription(db.Model):
    __tablename__ = "client_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id"),
        unique=True, nullable=False
    )
    plan_id = db.Column(
        db.Integer, db.ForeignKey("plans.id"),
        nullable=False
    )
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "plan_id": self.plan_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }


# ===============================
# INIT SYSTEM
# ===============================
def init_auth_system(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "SQLALCHEMY_DATABASE_URI"
    )

    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("❌ SQLALCHEMY_DATABASE_URI no definida")

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
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

    # -------- REGISTER --------
    @app.route("/api/auth/register", methods=["POST"])
    def register():
        data = request.get_json()

        if not data:
            return jsonify({"error": "Payload vacío"}), 400

        if not data or not data.get("email") or not data.get("password"):
            return jsonify({"error": "Datos inválidos"}), 400

        if Client.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "Email ya registrado"}), 400

        client = Client(
            company_name=data["company_name"],
            email=data["email"],
            contact_name=data.get("contact_name"),
            phone=data.get("phone"),
            role="client"
        )
        client.set_password(data["password"])

        db.session.add(client)
        db.session.commit()

        default_plan = Plan.query.filter_by(code="cloud_assessment").first()
        if not default_plan:
            return jsonify({"error": "Plan por defecto no existe"}), 500

        subscription = ClientSubscription(
            client_id=client.id,
            plan_id=default_plan.id,
            is_active=True
        )
        db.session.add(subscription)
        db.session.commit()

        token = create_access_token(identity=str(client.id))

        return jsonify({
            "access_token": token,
            "client": client.to_dict(),
            "subscription": subscription.to_dict()
        }), 201

    # -------- LOGIN --------
    @app.route("/api/auth/login", methods=["POST"])
    def login():
        data = request.get_json()

        client = Client.query.filter_by(email=data.get("email")).first()

        if not client or not client.check_password(data.get("password")):
            return jsonify({"error": "Credenciales inválidas"}), 401

        token = create_access_token(identity=str(client.id))

        subscription = ClientSubscription.query.filter_by(
            client_id=client.id,
            is_active=True
        ).first()

        return jsonify({
            "access_token": token,
            "client": client.to_dict(),
            "subscription": subscription.to_dict() if subscription else None
        }), 200

    # -------- PROFILE UPDATE --------
    @app.route("/api/users/profile", methods=["PUT"])
    @jwt_required()
    def update_profile():
        client_id = int(get_jwt_identity())
        client = Client.query.get(client_id)

        data = request.get_json()

        if "contact_name" in data:
            client.contact_name = data["contact_name"]
        if "phone" in data:
            client.phone = data["phone"]
        if "email" in data:
            client.email = data["email"]
        if data.get("password"):
            client.set_password(data["password"])

        db.session.commit()
        return jsonify({"user": client.to_dict()}), 200

    # -------- MY PLAN --------
    @app.route("/api/me/plan", methods=["GET"])
    @jwt_required()
    def my_plan():
        client_id = int(get_jwt_identity())

        sub = ClientSubscription.query.filter_by(
            client_id=client_id, is_active=True
        ).first()

        if not sub:
            return jsonify({"error": "Sin plan activo"}), 404

        plan = Plan.query.get(sub.plan_id)

        return jsonify({
            "plan": {
                "code": plan.code,
                "name": plan.name,
                "description": plan.description,
                "monthly_price": float(plan.monthly_price)
            }
        }), 200

    # -------- MY FEATURES --------
    @app.route("/api/me/features", methods=["GET"])
    @jwt_required()
    def my_features():
        client_id = int(get_jwt_identity())

        sub = ClientSubscription.query.filter_by(
            client_id=client_id, is_active=True
        ).first()

        if not sub:
            return jsonify({"features": []}), 200

        plan = Plan.query.get(sub.plan_id)
        features = [f.code for f in plan.features] if plan else []

        return jsonify({"features": features}), 200

    # -------- ADMIN: LIST USERS --------
    @app.route("/api/admin/users", methods=["GET"])
    @jwt_required()
    def admin_users():
        admin_id = int(get_jwt_identity())

        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        users = Client.query.all()
        result = []

        for u in users:
            sub = ClientSubscription.query.filter_by(
                client_id=u.id, is_active=True
            ).first()

            plan = None
            if sub:
                p = Plan.query.get(sub.plan_id)
                plan = {"code": p.code, "name": p.name} if p else None

            result.append({
                "id": u.id,
                "email": u.email,
                "company_name": u.company_name,
                "role": u.role,
                "is_active": u.is_active,
                "plan": plan
            })

        return jsonify({"users": result}), 200
    # ---------------------------------------------
    # ADMIN — ACTUALIZAR PLAN DE USUARIO
    # ---------------------------------------------
    @app.route('/api/admin/users/<int:user_id>/plan', methods=['PUT'])
    @jwt_required()
    def admin_update_user_plan(user_id):
        admin_id = int(get_jwt_identity())

        if not require_admin(admin_id):
            return jsonify({"error": "Acceso denegado"}), 403

        data = request.get_json()
        plan_code = data.get("plan_code")

        if not plan_code:
            return jsonify({"error": "plan_code requerido"}), 400

        plan = Plan.query.filter_by(code=plan_code, is_active=True).first()
        if not plan:
            return jsonify({"error": "Plan no encontrado"}), 404

        # 🔥 desactivar planes anteriores
        ClientSubscription.query.filter_by(
            client_id=user_id,
            is_active=True
        ).update({"is_active": False})

        # crear nueva suscripción
        subscription = ClientSubscription(
            client_id=user_id,
            plan_id=plan.id,
            is_active=True
        )

        db.session.add(subscription)
        db.session.commit()

        return jsonify({
            "message": "Plan actualizado correctamente",
            "user_id": user_id,
            "plan": {
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

        user.company_name = data.get("company_name", user.company_name)
        user.contact_name = data.get("contact_name", user.contact_name)
        user.phone = data.get("phone", user.phone)

        # 🔐 Evitar que admin se quite su propio rol
        if "role" in data:
            if user.id == admin_id:
                return jsonify({"error": "No puedes modificar tu propio rol"}), 400
            user.role = data["role"]

        # 🧠 Logging
        app.logger.info(
            f"Admin {admin_id} actualizó usuario {user_id}"
        )

        db.session.commit()

        return jsonify({
            "message": "Usuario actualizado correctamente",
            "user_id": user.id
        }), 200


    return app

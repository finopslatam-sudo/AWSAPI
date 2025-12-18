from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from flask_migrate import Migrate
from datetime import datetime
import bcrypt
import os

# Configuración de database separada
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


# ===============================
# MODELOS
# ===============================

class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    contact_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def to_dict(self):
        return {
            'id': self.id,
            'company_name': self.company_name,
            'email': self.email,
            'contact_name': self.contact_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }


class Plan(db.Model):
    __tablename__ = 'plans'

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
    __tablename__ = 'features'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)


class PlanFeature(db.Model):
    __tablename__ = 'plan_features'

    plan_id = db.Column(
        db.Integer, db.ForeignKey('plans.id'), primary_key=True
    )
    feature_id = db.Column(
        db.Integer, db.ForeignKey('features.id'), primary_key=True
    )


class ClientSubscription(db.Model):
    __tablename__ = 'client_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.Integer,
        db.ForeignKey('clients.id'),
        unique=True,
        nullable=False
    )
    plan_id = db.Column(
        db.Integer,
        db.ForeignKey('plans.id'),
        nullable=False
    )
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ===============================
# INICIALIZACIÓN
# ===============================

def init_auth_system(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'SQLALCHEMY_DATABASE_URI'
    )

    if not app.config['SQLALCHEMY_DATABASE_URI']:
        raise RuntimeError("❌ SQLALCHEMY_DATABASE_URI no está definida")

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['JWT_SECRET_KEY'] = os.getenv(
        'JWT_SECRET_KEY',
        'finopslatam-prod-secret'
    )

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

# ===============================
# RUTAS DE AUTENTICACIÓN
# ===============================

def create_auth_routes(app):

    # ---------------------------------------------
    # REGISTRO
    # ---------------------------------------------
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        try:
            data = request.get_json()

            if not data:
                return jsonify({'error': 'Datos requeridos'}), 400

            if not data.get('email') or not data.get('password'):
                return jsonify({'error': 'Email y password son requeridos'}), 400

            if not data.get('company_name'):
                return jsonify({'error': 'company_name es requerido'}), 400

            if Client.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'El email ya está registrado'}), 400

            client = Client(
                company_name=data['company_name'],
                email=data['email'],
                contact_name=data.get('contact_name', ''),
                phone=data.get('phone', '')
            )
            client.set_password(data['password'])

            db.session.add(client)
            db.session.commit()

            # Asignar plan por defecto (Cloud Assessment)
            default_plan = Plan.query.filter_by(code='cloud_assessment').first()

            if not default_plan:
                return jsonify({"error": "Plan por defecto no encontrado"}), 500

            subscription = ClientSubscription(
                client_id=client.id,
                plan_id=default_plan.id,
                is_active=True
            )

            db.session.add(subscription)
            db.session.commit()

            access_token = create_access_token(identity=str(client.id))

            return jsonify({
                'message': 'Cliente registrado exitosamente',
                'access_token': access_token,
                'client': client.to_dict(),
                'subscription': subscription.to_dict()
            }), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # ---------------------------------------------
    # ACTUALIZAR PERFIL
    # ---------------------------------------------
    @app.route('/api/users/profile', methods=['PUT'])
    @jwt_required()
    def update_user_profile():
        user_id = int(get_jwt_identity())

        data = request.get_json()

        client = Client.query.get(user_id)

        if not client or not client.is_active:
            return jsonify({"error": "Usuario no encontrado"}), 404

        if 'contact_name' in data:
            client.contact_name = data['contact_name']

        if 'phone' in data:
            client.phone = data['phone']

        if 'email' in data:
            existing = Client.query.filter_by(email=data['email']).first()
            if existing and existing.id != client.id:
                return jsonify({"error": "El email ya está en uso"}), 400
            client.email = data['email']

        if 'password' in data and data['password']:
            client.set_password(data['password'])

        db.session.commit()

        return jsonify({
            "message": "Perfil actualizado correctamente",
            "user": client.to_dict()
        }), 200

    # ---------------------------------------------
    # LOGIN
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
                'message': 'Login exitoso',
                'access_token': access_token,
                'client': client.to_dict(),
                'subscription': subscription.to_dict() if subscription else None
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    # ---------------------------------------------
    # MI PLAN ACTUAL
    # ---------------------------------------------
    @app.route('/api/me/plan', methods=['GET'])
    @jwt_required()
    def get_my_plan():
        client_id = int(get_jwt_identity())

        subscription = (
            ClientSubscription.query
            .filter_by(client_id=client_id, is_active=True)
            .first()
        )

        if not subscription:
            return jsonify({"error": "No tienes un plan activo"}), 404

        plan = Plan.query.get(subscription.plan_id)

        if not plan or not plan.is_active:
            return jsonify({"error": "Plan no disponible"}), 404
        
        features = [f.code for f in plan.features] if plan.features else []

        return jsonify({
            "plan": {
                "code": plan.code,
                "name": plan.name,
                "description": plan.description,
                "monthly_price": float(plan.monthly_price)
            }
        }), 200

    # ---------------------------------------------
    # FEATURES DISPONIBLES
    # ---------------------------------------------
    @app.route('/api/me/features', methods=['GET'])
    @jwt_required()
    def get_my_features():
        client_id = int(get_jwt_identity())

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
            "plan": plan.code,
            "features": features
        }), 200

    return app
    # ---------------------------------------------
    # PERFIL
    # ---------------------------------------------
    @app.route('/api/auth/profile', methods=['GET'])
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

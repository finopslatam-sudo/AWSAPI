from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from flask_migrate import Migrate
from datetime import datetime
import bcrypt
import os

# ===============================
# CONFIGURACIÓN GLOBAL
# ===============================

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active = db.Column(db.Boolean, default=True)
    
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
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }


class SubscriptionTier:
    ASSESSMENT = "assessment"
    INTELLIGENCE = "intelligence"


class ClientSubscription(db.Model):
    __tablename__ = 'client_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'),
                          unique=True, nullable=False)
    tier = db.Column(db.String(20), nullable=False,
                     default=SubscriptionTier.ASSESSMENT)
    monthly_price = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'tier': self.tier,
            'monthly_price': float(self.monthly_price),
            'is_active': self.is_active
        }


# ===============================
# INICIALIZACIÓN
# ===============================

def init_auth_system(app):
    """Inicializa el sistema de auth sin afectar tu app existente"""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finops_auth.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv(
        'JWT_SECRET_KEY', 'super-secret-jwt-key-change-in-production'
    )
    
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    # Crear tablas automáticamente en desarrollo
    with app.app_context():
        db.create_all()
    
    return app


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
            
            subscription = ClientSubscription(
                client_id=client.id,
                tier=SubscriptionTier.ASSESSMENT,
                monthly_price=499.00
            )
            db.session.add(subscription)
            db.session.commit()
            
            access_token = create_access_token(identity=client.id)
            
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
            
            access_token = create_access_token(identity=client.id)
            
            return jsonify({
                'message': 'Login exitoso',
                'access_token': access_token,
                'client': client.to_dict(),
                'subscription': subscription.to_dict() if subscription else None
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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

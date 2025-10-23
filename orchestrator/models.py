from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    credentials = db.relationship('Credential', backref='user', cascade='all, delete-orphan')
    containers = db.relationship('BotContainer', backref='user', cascade='all, delete-orphan')

class Credential(db.Model):
    __tablename__ = 'credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Encrypted credentials
    api_key_encrypted = db.Column(db.Text, nullable=False)
    api_secret_encrypted = db.Column(db.Text, nullable=False)
    
    # Trading config
    symbol = db.Column(db.String(20), default='BTCUSD')
    lot_size = db.Column(db.Float, default=60.0)
    timeframe = db.Column(db.Integer, default=15)
    delta_region = db.Column(db.String(20), default='india')
    testnet = db.Column(db.Boolean, default=False)
    
    # Telegram (optional)
    telegram_token_encrypted = db.Column(db.Text)
    telegram_chat_id = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BotContainer(db.Model):
    __tablename__ = 'bot_containers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    credential_id = db.Column(db.Integer, db.ForeignKey('credentials.id'), nullable=False)
    
    container_id = db.Column(db.String(64), unique=True)
    container_name = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default='running')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    stopped_at = db.Column(db.DateTime)
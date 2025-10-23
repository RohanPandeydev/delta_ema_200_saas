"""
Flask extensions initialization
"""
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_socketio import SocketIO
from celery import Celery

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')
celery = Celery()
# ============================================
# FILE: orchestrator/app.py
# ============================================
"""
Main Flask application
"""
from flask import Flask, render_template, redirect, url_for
from orchestrator.config import Config
from orchestrator.extensions import db, bcrypt, login_manager, socketio, celery
from orchestrator.models import User
import os

def create_app(config_class=Config):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    
    # Configure Celery
    celery.conf.update(app.config)
    
    # Login manager config
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please login to access this page'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from orchestrator.routes.auth import auth_bp
    from orchestrator.routes.dashboard import dashboard_bp
    from orchestrator.routes.credentials import credentials_bp
    from orchestrator.routes.webhook import webhook_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(credentials_bp)
    app.register_blueprint(webhook_bp)
    
    # Home route
    @app.route('/')
    def index():
        from flask_login import current_user
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    # SocketIO events for real-time logs
    @socketio.on('connect')
    def handle_connect():
        from flask_socketio import emit
        from flask_login import current_user
        if current_user.is_authenticated:
            emit('connected', {'data': 'Connected to log stream'})
    
    @socketio.on('subscribe_logs')
    def handle_subscribe_logs(data):
        from flask_socketio import emit, join_room
        from flask_login import current_user
        from orchestrator.models import BotContainer
        
        container_db_id = data.get('container_id')
        container = BotContainer.query.get(container_db_id)
        
        if container and container.user_id == current_user.id:
            room = f"logs_{container.container_id}"
            join_room(room)
            emit('subscribed', {'container_id': container_db_id})
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Login manager configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Register blueprints - MAKE SURE THIS IS CORRECT
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.bots import bots_bp
    from app.routes.payment import payment_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(bots_bp, url_prefix='/')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    
    return app
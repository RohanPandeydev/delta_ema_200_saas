import os
from datetime import timedelta
from urllib.parse import quote_plus

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ea7cbe2fbce91afd99ef626e03de54f4defe711951d9ce19e957232e60149219'
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or 'Urts4Q3EnVyVYeTefw2TLHsWyR8T8B4Zavh-Rgpi5Vg='
    
    # Database Configuration
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_PORT = os.environ.get('DB_PORT') or '3306'
    DB_NAME = os.environ.get('DB_NAME') or 'trading_bot_db'
    DB_USER = os.environ.get('DB_USER') or 'root'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or 'algodbadmin'
    
    # SQLAlchemy Database URI
    if os.environ.get('DATABASE_URL'):
        # Use provided DATABASE_URL (for production)
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    else:
        # Construct database URI from individual components
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20,
    }
    
    # Docker Configuration
    DOCKER_NETWORK = os.environ.get('DOCKER_NETWORK') or 'trading_bot_network'
    BOT_IMAGE = os.environ.get('BOT_IMAGE') or 'trading-bot:latest'
    DOCKER_BASE_URL = os.environ.get('DOCKER_BASE_URL')
    
    # Subscription/Premium Features
    REQUIRE_SUBSCRIPTION = os.environ.get('REQUIRE_SUBSCRIPTION', 'False').lower() == 'true'
    PREMIUM_PRICE = float(os.environ.get('PREMIUM_PRICE', '99.00'))
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application Settings
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    TESTING = os.environ.get('TESTING', 'False').lower() == 'true'
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
    }
    
    # CORS Configuration (if needed for APIs)
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    
    # Bot Default Settings
    DEFAULT_BOT_SETTINGS = {
        'timeframe': 15,
        'timeframe_type': 'm',
        'lot_size': 1.0,
        'api_port': 8080,
        'log_level': 'INFO',
        'log_file': 'trading_bot.log',
        'delta_region': 'india',
        'testnet': False,
    }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    DB_NAME = os.environ.get('DB_NAME') or 'trading_bot_db_dev'
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{Config.DB_USER}:{quote_plus(Config.DB_PASSWORD)}@{Config.DB_HOST}:{Config.DB_PORT}/{DB_NAME}"


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    DB_NAME = os.environ.get('DB_NAME') or 'trading_bot_db_test'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///:memory:"  # Use in-memory SQLite for tests
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    DB_NAME = os.environ.get('DB_NAME') or 'trading_bot_db'
    SESSION_COOKIE_SECURE = True
    
    # Use environment variable for production database
    if os.environ.get('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    else:
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{Config.DB_USER}:{quote_plus(Config.DB_PASSWORD)}@{Config.DB_HOST}:{Config.DB_PORT}/{DB_NAME}"


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])


# Export current config
current_config = get_config()
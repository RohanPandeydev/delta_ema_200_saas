"""
Configuration settings
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://trading_user:trading_password@db:3306/trading_bot_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Encryption
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    
    # Docker
    DOCKER_NETWORK = os.getenv('DOCKER_NETWORK', 'trading_bot_network')
    BOT_IMAGE = os.getenv('BOT_IMAGE', 'trading-bot:latest')
    
    # Subscription
    REQUIRE_SUBSCRIPTION = os.getenv('REQUIRE_SUBSCRIPTION', 'False').lower() == 'true'
    
    # SocketIO
    SOCKETIO_MESSAGE_QUEUE = None  # Not using Redis
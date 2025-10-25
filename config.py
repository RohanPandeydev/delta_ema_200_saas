import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ea7cbe2fbce91afd99ef626e03de54f4defe711951d9ce19e957232e60149219'
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or 'Urts4Q3EnVyVYeTefw2TLHsWyR8T8B4Zavh-Rgpi5Vg='
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://trading_user:trading_password@localhost:3306/trading_bot_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Docker
    DOCKER_NETWORK = os.environ.get('DOCKER_NETWORK') or 'trading_bot_network'
    BOT_IMAGE = os.environ.get('BOT_IMAGE') or 'trading-bot:latest'
    
    # Subscription
    REQUIRE_SUBSCRIPTION = os.environ.get('REQUIRE_SUBSCRIPTION', 'False').lower() == 'true'
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
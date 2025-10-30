from app import db
from datetime import datetime

class BotConfiguration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bot_type = db.Column(db.Enum('EMA', 'RSI_SMA'), nullable=False)
    bot_name = db.Column(db.String(100), nullable=False)
    container_id = db.Column(db.String(255))
    container_name = db.Column(db.String(255))
    status = db.Column(db.Enum('stopped', 'running', 'error'), default='stopped')
    
    # Delta Exchange API Credentials
    delta_api_key = db.Column(db.String(255), nullable=False)
    delta_api_secret = db.Column(db.String(255), nullable=False)
    delta_region = db.Column(db.String(50), default='india')
    
    # Common Trading Configuration (Both Bots)
    symbol = db.Column(db.String(20), default='BTCUSD')
    lot_size = db.Column(db.Float, default=1.0)  # Changed to Float for decimal values
    timeframe = db.Column(db.Integer, default=15)  # Unified timeframe
    timeframe_type = db.Column(db.String(5), default='m')  # m for minutes
    
    # Exchange Settings
    testnet = db.Column(db.Boolean, default=False)
    
    # Telegram Notifications
    telegram_bot_token = db.Column(db.String(255))
    telegram_chat_id = db.Column(db.String(100))
    
    # HTTP API Configuration
    api_port = db.Column(db.Integer, default=8080)
    
    # Logging Configuration
    log_level = db.Column(db.String(20), default='INFO')
    log_file = db.Column(db.String(255), default='trading_bot.log')
    
    # EMA Bot Specific
    ema_period = db.Column(db.Integer, default=200)
    
    # RSI_SMA Bot Specific
    rsi_period = db.Column(db.Integer, default=14)
    rsi_overbought = db.Column(db.Integer, default=70)
    rsi_oversold = db.Column(db.Integer, default=30)
    sma_period = db.Column(db.Integer, default=21)
    
    # TradingView Fallback Settings
    tv_symbol = db.Column(db.String(20), default='BTCUSDT')
    use_tradingview_fallback = db.Column(db.Boolean, default=True)
    
    # TAAPI Configuration
    taapi_secret_key = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'bot_type': self.bot_type,
            'bot_name': self.bot_name,
            'status': self.status,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timeframe_type': self.timeframe_type,
            'lot_size': self.lot_size,
            'container_name': self.container_name,
            'testnet': self.testnet,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def __repr__(self):
        return f'<Bot {self.bot_name} ({self.bot_type})>'
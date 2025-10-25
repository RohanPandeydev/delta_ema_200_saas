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
    
    # Common Configuration (Both Bots)
    delta_api_key = db.Column(db.String(255), nullable=False)
    delta_api_secret = db.Column(db.String(255), nullable=False)
    symbol = db.Column(db.String(20), default='BTCUSD')
    timeframe = db.Column(db.String(10), default='15')
    telegram_bot_token = db.Column(db.String(255))
    telegram_chat_id = db.Column(db.String(100))
    lot_size = db.Column(db.String(20), default='3.0')
    
    # EMA Bot Specific
    ema_period = db.Column(db.Integer)
    
    # RSI_SMA Bot Specific
    rsi_period = db.Column(db.Integer)
    rsi_overbought = db.Column(db.Integer)
    rsi_oversold = db.Column(db.Integer)
    sma_period = db.Column(db.Integer)
    timeframe_candle_m = db.Column(db.String(10), default='0')
    
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
            'container_name': self.container_name,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def __repr__(self):
        return f'<Bot {self.bot_name} ({self.bot_type})>'
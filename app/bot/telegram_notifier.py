import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv()

class TelegramNotifier:
    def __init__(self, bot_token=None, chat_id=None):
        # Telegram settings
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
        
        # Get container information from environment
        self.container_id = os.environ.get('CONTAINER_ID', 'unknown')
        self.bot_type = os.environ.get('BOT_TYPE', 'unknown')
        self.symbol = os.environ.get('SYMBOL', 'unknown')
    
    def _write_log(self, message):
        """Write formatted log message to stdout"""
        # Create standardized log format
        log_prefix = f"[{self.bot_type}:{self.symbol}] "
        formatted_msg = f"{log_prefix}{message}"
        
        # Write to stdout (will be captured by Docker)
        print(formatted_msg, flush=True)
        sys.stdout.flush()  # Ensure immediate flushing
    
    def send_message(self, message):
        """Send message to both Telegram and logs"""
        # Always write to logs
        self._write_log(message)
        
        # Send to Telegram if enabled
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except:
            return False
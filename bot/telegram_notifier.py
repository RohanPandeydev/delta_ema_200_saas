"""
Telegram Notification Module for EMA Trading Bot
Add this to your existing bot to get real-time trade notifications
"""
import requests
from datetime import datetime
from colorama import Fore


class TelegramNotifier:
    """Handles Telegram notifications for trade events"""
    
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.enabled = bool(bot_token and chat_id)
        
        if self.enabled:
            self._test_connection()
    
    def _test_connection(self):
        """Test Telegram bot connection"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_name = data['result']['username']
                    print(f"{Fore.GREEN}✅ Telegram bot connected: @{bot_name}")
                    return True
        except Exception as e:
            print(f"{Fore.RED}❌ Telegram connection failed: {e}")
            self.enabled = False
        return False
    
    def send_message(self, message, parse_mode='HTML'):
        """Send message to Telegram"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"{Fore.RED}⚠️  Telegram send failed: {e}")
            return False
    
    def notify_bot_start(self, symbol, timeframe, ema_period, lot_size):
        """Notify when bot starts"""
        message = f"""
🤖 <b>EMA TRADING BOT STARTED</b>

📊 <b>Configuration:</b>
• Symbol: {symbol}
• Timeframe: {timeframe} minutes
• EMA Period: {ema_period}
• Lot Size: {lot_size}
• Execution: Best Bid/Ask

⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message.strip())
    
    def notify_signal(self, signal, price, ema, candle_time):
        """Notify when new signal is detected"""
        emoji = "🟢" if signal == "LONG" else "🔴"
        diff = abs(price - ema)
        position = "ABOVE" if price > ema else "BELOW"
        
        message = f"""
{emoji} <b>NEW SIGNAL: {signal}</b>

📊 <b>Analysis:</b>
• Price: ${price:,.2f}
• EMA-200: ${ema:,.2f}
• Difference: ${diff:,.2f} {position}

⏰ Candle: {datetime.fromtimestamp(candle_time).strftime('%Y-%m-%d %H:%M:%S')}

⏳ Will execute on next candle open
"""
        self.send_message(message.strip())
    
    def notify_order_placed(self, side, size, price, order_id):
        """Notify when order is placed"""
        emoji = "📈" if side.upper() == "BUY" else "📉"
        
        message = f"""
{emoji} <b>ORDER PLACED</b>

🎯 <b>Details:</b>
• Side: {side.upper()}
• Size: {size}
• Price: ${price:,.2f}
• Order ID: {order_id}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        self.send_message(message.strip())
    
    def notify_position_opened(self, direction, size, price, orderbook=None):
        """Notify when position is opened"""
        emoji = "✅" if direction == "LONG" else "🔻"
        
        spread_info = ""
        if orderbook:
            spread_info = f"\n• Spread: ${orderbook['spread']:.2f}"
        
        message = f"""
{emoji} <b>POSITION OPENED: {direction}</b>

💼 <b>Position Details:</b>
• Direction: {direction}
• Size: {size}
• Entry Price: ${price:,.2f}{spread_info}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message.strip())
    
    def notify_position_closed(self, direction, size, entry_price, exit_price, pnl):
        """Notify when position is closed"""
        emoji = "💰" if pnl >= 0 else "⚠️"
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        
        message = f"""
{emoji} <b>POSITION CLOSED: {direction}</b>

📊 <b>Trade Summary:</b>
• Direction: {direction}
• Size: {size}
• Entry: ${entry_price:,.2f}
• Exit: ${exit_price:,.2f}

{pnl_emoji} <b>P&L: ${pnl:,.2f}</b>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message.strip())
    
    def notify_error(self, error_message):
        """Notify when error occurs"""
        message = f"""
❌ <b>ERROR DETECTED</b>

⚠️ {error_message}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(message.strip())
    
    def notify_trade_summary(self, total_trades, win_count=None, loss_count=None):
        """Send periodic trade summary"""
        message = f"""
📊 <b>TRADE SUMMARY</b>

🔢 Total Trades: {total_trades}
"""
        if win_count is not None and loss_count is not None:
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
            message += f"""✅ Wins: {win_count}
❌ Losses: {loss_count}
📈 Win Rate: {win_rate:.1f}%
"""
        
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.send_message(message.strip())
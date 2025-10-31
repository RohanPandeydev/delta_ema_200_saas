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
                    
                    # Send connection message
                    self._send_connected_message(bot_name)
                    return True
        except Exception as e:
            print(f"{Fore.RED}❌ Telegram connection failed: {e}")
            self.enabled = False
        return False
    
    def _send_connected_message(self, bot_name):
        """Send bot connected message"""
        message = f"""
🤖 <b>BOT CONNECTED SUCCESSFULLY</b>

✅ Telegram notifications are now active
🤖 Bot: @{bot_name}
🔔 Ready to receive trade signals

⏰ Connected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message.strip())
    
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
• Timeframe: {timeframe}
• EMA Period: {ema_period}
• Lot Size: {lot_size}
• Execution: Best Bid/Ask

⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message.strip())
    
    def notify_crossover_detected(self, crossover_type, current_price, current_ema, prev_price, prev_ema):
        """Notify when EMA crossover is detected"""
        if crossover_type == "BULLISH":
            emoji = "🟢"
            action = "BULLISH CROSSOVER"
            description = "Price crossed ABOVE EMA"
            signal = "LONG"
        else:  # BEARISH
            emoji = "🔴"
            action = "BEARISH CROSSOVER"
            description = "Price crossed BELOW EMA"
            signal = "SHORT"
        
        price_change = current_price - prev_price
        ema_change = current_ema - prev_ema
        
        message = f"""
{emoji} <b>{action} DETECTED!</b>

📈 <b>Signal: {signal}</b>

📊 <b>Current Values:</b>
• Price: ${current_price:,.2f}
• EMA-{self.ema_period}: ${current_ema:,.2f}
• Position: Price is {'ABOVE' if current_price > current_ema else 'BELOW'} EMA

📊 <b>Changes from previous candle:</b>
• Price: ${prev_price:,.2f} → ${current_price:,.2f} ({price_change:+.2f})
• EMA: ${prev_ema:,.2f} → ${current_ema:,.2f} ({ema_change:+.2f})

✅ <b>Status:</b> {description}

⏳ <b>Action:</b> Preparing to execute {signal} position...

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_message(message.strip())
    
    def notify_signal(self, signal, price, ema, candle_time):
        """Notify when new signal is detected"""
        emoji = "🟢" if signal == "LONG" else "🔴"
        diff = abs(price - ema)
        position = "ABOVE" if price > ema else "BELOW"
        
        message = f"""
{emoji} <b>NEW SIGNAL: {signal}</b>

📊 <b>Analysis:</b>
• Price: ${price:,.2f}
• EMA-{self.ema_period}: ${ema:,.2f}
• Difference: ${diff:,.2f} {position}

⏰ Candle: {datetime.fromtimestamp(candle_time).strftime('%Y-%m-%d %H:%M:%S')}

⏳ Will execute on next candle open
"""
        return self.send_message(message.strip())
    
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
        return self.send_message(message.strip())
    
    def notify_position_opened(self, direction, size, price, ema_value, orderbook=None):
        """Notify when position is opened"""
        emoji = "✅" if direction == "LONG" else "🔻"
        
        spread_info = ""
        if orderbook:
            spread_info = f"\n• Spread: ${orderbook['spread']:.4f}"
        
        message = f"""
{emoji} <b>POSITION OPENED: {direction}</b>

💼 <b>Position Details:</b>
• Direction: {direction}
• Size: {size}
• Entry Price: ${price:,.2f}{spread_info}

📊 <b>Market Conditions:</b>
• EMA-{self.ema_period}: ${ema_value:,.2f}
• Price vs EMA: {'ABOVE' if price > ema_value else 'BELOW'}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message.strip())
    
    def notify_position_closed(self, direction, size, entry_price, exit_price, pnl, ema_value):
        """Notify when position is closed"""
        emoji = "💰" if pnl >= 0 else "⚠️"
        pnl_emoji = "📈" if pnl >= 0 else "📉"
        result = "PROFIT" if pnl >= 0 else "LOSS"
        
        price_change = exit_price - entry_price
        price_change_pct = (price_change / entry_price * 100) if entry_price > 0 else 0
        
        message = f"""
{emoji} <b>POSITION CLOSED: {direction}</b>

📊 <b>Trade Summary:</b>
• Direction: {direction}
• Size: {size}
• Entry: ${entry_price:,.2f}
• Exit: ${exit_price:,.2f}
• Price Change: ${price_change:,.2f} ({price_change_pct:+.2f}%)

📈 <b>Market at Exit:</b>
• EMA-{self.ema_period}: ${ema_value:,.2f}
• Exit Price vs EMA: {'ABOVE' if exit_price > ema_value else 'BELOW'}

{pnl_emoji} <b>Result: {result}</b>
💵 <b>P&L: ${pnl:,.2f}</b>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message.strip())
    
    def notify_error(self, error_message):
        """Notify when error occurs"""
        message = f"""
❌ <b>ERROR DETECTED</b>

⚠️ {error_message}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message.strip())
    
    def notify_trade_summary(self, total_trades, win_count=None, loss_count=None, total_pnl=None):
        """Send periodic trade summary"""
        message = f"""
📊 <b>TRADE SUMMARY</b>

🔢 Total Trades: {total_trades}
"""
        if win_count is not None and loss_count is not None:
            closed_trades = win_count + loss_count
            win_rate = (win_count / closed_trades * 100) if closed_trades > 0 else 0
            message += f"""• Closed Trades: {closed_trades}
✅ Wins: {win_count}
❌ Losses: {loss_count}
📈 Win Rate: {win_rate:.1f}%
"""
        
        if total_pnl is not None:
            pnl_emoji = "💰" if total_pnl >= 0 else "📉"
            message += f"""{pnl_emoji} Total P&L: ${total_pnl:,.2f}
"""
        
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(message.strip())
    
    def notify_bot_shutdown(self, total_trades, wins, losses, total_pnl):
        """Notify when bot is shutting down"""
        closed_trades = wins + losses
        win_rate = (wins / closed_trades * 100) if closed_trades > 0 else 0
        
        pnl_emoji = "💰" if total_pnl >= 0 else "📉"
        result = "PROFITABLE" if total_pnl >= 0 else "LOSS"
        
        message = f"""
🛑 <b>BOT SHUTDOWN</b>

📊 <b>Final Statistics:</b>
• Total Trades: {total_trades}
• Closed Trades: {closed_trades}
• Wins: {wins}
• Losses: {losses}
• Win Rate: {win_rate:.1f}%

{pnl_emoji} <b>Final Result: {result}</b>
💵 Total P&L: ${total_pnl:,.2f}

⏰ Stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ Bot stopped successfully
"""
        return self.send_message(message.strip())
    
    def notify_crossover_analysis(self, current_price, current_ema, prev_price, prev_ema, trend_strength):
        """Notify detailed crossover analysis"""
        price_trend = "BULLISH" if current_price > prev_price else "BEARISH"
        ema_trend = "RISING" if current_ema > prev_ema else "FALLING"
        
        price_distance = abs(current_price - current_ema)
        distance_pct = (price_distance / current_ema * 100) if current_ema > 0 else 0
        
        message = f"""
📊 <b>CROSSOVER ANALYSIS</b>

🔍 <b>Market Analysis:</b>
• Current Price: ${current_price:,.2f}
• EMA-{self.ema_period}: ${current_ema:,.2f}
• Price Distance: ${price_distance:,.2f} ({distance_pct:.2f}%)
• Price Trend: {price_trend}
• EMA Trend: {ema_trend}

💪 <b>Trend Strength:</b> {trend_strength}

📈 <b>Signal:</b> {'LONG' if current_price > current_ema else 'SHORT'}
• Position: Price is {'ABOVE' if current_price > current_ema else 'BELOW'} EMA

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_message(message.strip())
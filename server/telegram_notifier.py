"""
Enhanced Telegram Notification Module for RSI-SMA Trading Bot
Optimized for crossover signals and trade notifications
"""
import requests
from datetime import datetime
from colorama import Fore


class TelegramNotifier:
    """Handles Telegram notifications for RSI-SMA trade events"""
    
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.enabled = bool(bot_token and chat_id)
        
        if self.enabled:
            self._test_connection()
    
    def _test_connection(self):
        """Test Telegram bot connection and send connected message"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_name = data['result']['username']
                    print(f"{Fore.GREEN}✅ Telegram bot connected: @{bot_name}")
                    
                    # Send connection success message
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
    
    def notify_bot_start(self, symbol, timeframe, rsi_period, sma_period, lot_size):
        """Notify when bot starts"""
        message = f"""
🤖 <b>RSI-SMA BOT STARTED</b>

📊 <b>Configuration:</b>
• Symbol: {symbol}
• Timeframe: {timeframe}
• RSI Period: {rsi_period}
• SMA Period: {sma_period}
• Lot Size: {lot_size}
• Method: TradingView Exact (Wilder's RMA)

⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 Strategy: RSI crosses above/below SMA
"""
        return self.send_message(message.strip())
    
    def notify_crossover(self, signal, prev_rsi, current_rsi, prev_sma, current_sma, price):
        """Notify when RSI-SMA crossover is detected"""
        if signal == 'LONG':
            emoji = "🟢"
            color_symbol = "🔺"
            action = "BULLISH CROSSOVER"
            description = "RSI crossed ABOVE SMA"
        else:
            emoji = "🔴"
            color_symbol = "🔻"
            action = "BEARISH CROSSOVER"
            description = "RSI crossed BELOW SMA"
        
        rsi_change = current_rsi - prev_rsi
        sma_change = current_sma - prev_sma
        
        message = f"""
{emoji} <b>{action} DETECTED!</b>

{color_symbol} <b>Signal: {signal} ENTRY</b>

📊 <b>Indicator Values:</b>
• RSI: {prev_rsi:.2f} → {current_rsi:.2f} ({rsi_change:+.2f})
• SMA: {prev_sma:.2f} → {current_sma:.2f} ({sma_change:+.2f})

💵 <b>Price:</b> ${price:,.2f}

✅ <b>Status:</b> {description}

⏳ <b>Action:</b> Opening {signal} position...

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_message(message.strip())
    
    def notify_position_opened(self, direction, size, price, rsi, sma, orderbook=None):
        """Notify when position is opened"""
        emoji = "✅" if direction == "LONG" else "🔻"
        
        spread_info = ""
        if orderbook:
            spread_info = f"\n• Spread: ${orderbook['spread']:.4f}"
            if direction == "LONG":
                spread_info += f"\n• Entry at: Best Ask"
            else:
                spread_info += f"\n• Entry at: Best Bid"
        
        message = f"""
{emoji} <b>POSITION OPENED: {direction}</b>

💼 <b>Position Details:</b>
• Direction: {direction}
• Size: {size} contracts
• Entry Price: ${price:,.2f}{spread_info}

📊 <b>Indicators at Entry:</b>
• RSI: {rsi:.2f}
• SMA: {sma:.2f}
• Position: RSI {'>' if rsi > sma else '<'} SMA

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(message.strip())
    
    def notify_position_closed(self, direction, size, entry_price, exit_price, pnl):
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
• Size: {size} contracts
• Entry: ${entry_price:,.2f}
• Exit: ${exit_price:,.2f}
• Price Change: ${price_change:,.2f} ({price_change_pct:+.2f}%)

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
📊 <b>PERIODIC TRADE SUMMARY</b>

🔢 <b>Trading Statistics:</b>
• Total Trades: {total_trades}
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
"""
Telegram Notifier - Enhanced with Profit Percentage and Amount
"""
import requests
from datetime import datetime
import pytz


class TelegramNotifier:
    """Send trading notifications via Telegram with detailed P&L info"""
    
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)
        self.base_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.timezone = pytz.timezone('Asia/Kolkata')
        
        if self.enabled:
            print(f"✅ Telegram notifications enabled for chat {chat_id}")
        else:
            print(f"⚠️ Telegram notifications disabled (missing token or chat_id)")
    
    def _send_message(self, message):
        """Send message to Telegram"""
        if not self.enabled:
            return False
        
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(self.base_url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Telegram error: {e}")
            return False
    
    def _get_timestamp(self):
        """Get current IST timestamp"""
        return datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S IST')
    
    def notify_bot_start(self, symbol, timeframe, rsi_period, sma_period, lot_size):
        """Notify bot startup"""
        message = f"""
🚀 <b>BOT STARTED</b>

📊 <b>Configuration</b>
• Symbol: {symbol}
• Timeframe: {timeframe}
• RSI Period: {rsi_period}
• SMA Period: {sma_period}
• Lot Size: {lot_size} contracts

⏰ {self._get_timestamp()}
"""
        self._send_message(message)
    
    def notify_crossover(self, signal, prev_rsi, current_rsi, prev_sma, current_sma, price):
        """Notify RSI-SMA crossover"""
        emoji = "🟢" if signal == "LONG" else "🔴"
        direction = "BULLISH" if signal == "LONG" else "BEARISH"
        
        message = f"""
{emoji} <b>{direction} CROSSOVER DETECTED</b>

📈 <b>Indicator Values</b>
• RSI: {prev_rsi:.2f} → {current_rsi:.2f}
• SMA: {prev_sma:.2f} → {current_sma:.2f}
• RSI Change: {current_rsi - prev_rsi:+.2f}

💰 <b>Price</b>
• Current: ${price:,.2f}

🎯 <b>Signal: {signal}</b>

⏰ {self._get_timestamp()}
"""
        self._send_message(message)
    
    def notify_position_opened(self, direction, size, price, rsi, sma, orderbook):
        """Notify position opened"""
        emoji = "📈" if direction == "LONG" else "📉"
        
        message = f"""
{emoji} <b>{direction} POSITION OPENED</b>

💼 <b>Position Details</b>
• Direction: {direction}
• Size: {size} contracts
• Entry Price: ${price:,.2f}
• Total Value: ${price * size:,.2f}

📊 <b>Indicators</b>
• RSI: {rsi:.2f}
• SMA: {sma:.2f}

📖 <b>Orderbook</b>
• Best Bid: ${orderbook['best_bid']:,.2f}
• Best Ask: ${orderbook['best_ask']:,.2f}
• Spread: ${orderbook['spread']:.2f}

⏰ {self._get_timestamp()}
"""
        self._send_message(message)
    
    def notify_position_closed(self, direction, size, entry_price, exit_price, pnl):
        """Notify position closed with P&L details"""
        # Calculate percentage profit
        if entry_price > 0:
            if direction == "LONG":
                pnl_percentage = ((exit_price - entry_price) / entry_price) * 100
            else:  # SHORT
                pnl_percentage = ((entry_price - exit_price) / entry_price) * 100
        else:
            pnl_percentage = 0
        
        # Determine emoji based on profit/loss
        if pnl > 0:
            emoji = "✅"
            result = "PROFIT"
            color = "🟢"
        elif pnl < 0:
            emoji = "❌"
            result = "LOSS"
            color = "🔴"
        else:
            emoji = "➖"
            result = "BREAKEVEN"
            color = "⚪"
        
        message = f"""
{emoji} <b>{direction} POSITION CLOSED</b>

💼 <b>Position Details</b>
• Direction: {direction}
• Size: {size} contracts
• Entry: ${entry_price:,.2f}
• Exit: ${exit_price:,.2f}
• Price Change: ${exit_price - entry_price:+,.2f}

{color} <b>{result}</b>
• P&L Amount: ${pnl:+,.2f}
• P&L Percentage: {pnl_percentage:+.2f}%
• Total Value Traded: ${entry_price * size:,.2f}
+
⏰ {self._get_timestamp()}
"""
        self._send_message(message)
    
    def notify_trade_summary(self, total_trades, win_count, loss_count, total_pnl):
        """Notify periodic trade summary"""
        total_closed = win_count + loss_count
        win_rate = (win_count / total_closed * 100) if total_closed > 0 else 0
        
        emoji = "📊"
        if total_pnl > 0:
            pnl_emoji = "🟢"
        elif total_pnl < 0:
            pnl_emoji = "🔴"
        else:
            pnl_emoji = "⚪"
        
        message = f"""
{emoji} <b>TRADING SUMMARY</b>

📈 <b>Performance</b>
• Total Trades: {total_trades}
• Closed Trades: {total_closed}
• Wins: {win_count} ✅
• Losses: {loss_count} ❌
• Win Rate: {win_rate:.1f}%

{pnl_emoji} <b>P&L</b>
• Total P&L: ${total_pnl:+,.2f}
• Avg Per Trade: ${(total_pnl / total_closed):+,.2f} (closed trades)

⏰ {self._get_timestamp()}
"""
        self._send_message(message)
    
    def notify_bot_shutdown(self, total_trades, wins, losses, total_pnl):
        """Notify bot shutdown"""
        total_closed = wins + losses
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
        
        message = f"""
🛑 <b>BOT STOPPED</b>

📊 <b>Final Statistics</b>
• Total Trades: {total_trades}
• Closed Trades: {total_closed}
• Wins: {wins}
• Losses: {losses}
• Win Rate: {win_rate:.1f}%
• Total P&L: ${total_pnl:+,.2f}

⏰ {self._get_timestamp()}
"""
        self._send_message(message)
    
    def notify_error(self, error_message):
        """Notify error"""
        message = f"""
⚠️ <b>ERROR OCCURRED</b>

{error_message}

⏰ {self._get_timestamp()}
"""
        self._send_message(message)
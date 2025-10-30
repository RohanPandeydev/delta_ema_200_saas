"""
EMA-200 Strategy Trading Bot for Delta Exchange - PRODUCTION VERSION
Fixed: Accurate EMA calculation with proper initialization
Enhanced: Order monitoring and automatic replacement
New: Flexible timeframe support (minutes, hours, days, weeks, months)
"""
import requests
import time
import hmac
import hashlib
import json
from datetime import datetime
from collections import deque
from config import Config
from colorama import init, Fore, Style
from telegram_notifier import TelegramNotifier

init(autoreset=True)


class TimeframeConverter:
    """Convert various timeframe types to API format and minutes"""
    
    @staticmethod
    def parse_timeframe(value, timeframe_type):
        """
        Parse timeframe value and type into API resolution and minutes
        
        Args:
            value: numeric value (e.g., 60, 1, 4)
            timeframe_type: 'm' (minutes), 'h' (hours), 'd' (days), 'w' (weeks), 'mm' (months)
        
        Returns:
            tuple: (api_resolution, total_minutes)
        """
        timeframe_type = timeframe_type.lower()
        
        # Convert to minutes based on type
        if timeframe_type == 'm':
            # Minutes
            total_minutes = value
            resolution = f'{value}m'
            
        elif timeframe_type == 'h':
            # Hours
            total_minutes = value * 60
            resolution = f'{value}h'
            
        elif timeframe_type == 'd':
            # Days
            total_minutes = value * 24 * 60
            resolution = f'{value}d'
            
        elif timeframe_type == 'w':
            # Weeks
            total_minutes = value * 7 * 24 * 60
            resolution = f'{value}w'
            
        elif timeframe_type == 'mm':
            # Months (approximate as 30 days)
            total_minutes = value * 30 * 24 * 60
            resolution = f'{value}M'  # Capital M for months in some APIs
            
        else:
            raise ValueError(f"Unsupported timeframe type: {timeframe_type}")
        
        return resolution, int(total_minutes)
    
    @staticmethod
    def format_timeframe_display(value, timeframe_type):
        """Format timeframe for human-readable display"""
        timeframe_type = timeframe_type.lower()
        
        if timeframe_type == 'm':
            if value >= 60:
                hours = value / 60
                return f"{hours:.1f}h" if hours != int(hours) else f"{int(hours)}h"
            return f"{value}m"
        elif timeframe_type == 'h':
            if value >= 24:
                days = value / 24
                return f"{days:.1f}d" if days != int(days) else f"{int(days)}d"
            return f"{value}h"
        elif timeframe_type == 'd':
            if value >= 7:
                weeks = value / 7
                return f"{weeks:.1f}w" if weeks != int(weeks) else f"{int(weeks)}w"
            return f"{value}d"
        elif timeframe_type == 'w':
            return f"{value}w"
        elif timeframe_type == 'mm':
            return f"{value}M"
        
        return f"{value}{timeframe_type}"


class TradeRecord:
    """Record for tracking individual trades"""
    def __init__(self, trade_id, timestamp, action, side, size, price, position_type, ema_value, close_price):
        self.trade_id = trade_id
        self.timestamp = timestamp
        self.action = action  # 'OPEN' or 'CLOSE'
        self.side = side  # 'buy' or 'sell'
        self.size = size
        self.price = price
        self.position_type = position_type  # 'LONG' or 'SHORT'
        self.ema_value = ema_value
        self.close_price = close_price
        self.pnl = None

    def __str__(self):
        pnl_str = f"P&L: ${self.pnl:,.2f}" if self.pnl is not None else "Open"
        return (f"[{self.timestamp}] {self.action} {self.position_type} | "
                f"{self.side.upper()} {self.size} @ ${self.price:,.2f} | "
                f"EMA: ${self.ema_value:,.2f} | {pnl_str}")


class EMAStrategyBot:
    """Production EMA-200 trading bot with accurate EMA calculation and order monitoring"""

    def __init__(self):
        self._print_header()

        self.base_url = Config.get_base_url()
        self.api_key = Config.DELTA_API_KEY
        self.api_secret = Config.DELTA_API_SECRET

        # STRATEGY PARAMETERS
        self.symbol = Config.SYMBOL
        self.lot_size = Config.LOT_SIZE
        self.ema_period = Config.EMA
        
        # Parse timeframe
        timeframe_value = Config.TIMEFRAME
        timeframe_type = Config.TIMEFRAME_TYPE
        
        self.resolution, self.TIMEFRAME_MINUTES = TimeframeConverter.parse_timeframe(
            timeframe_value, timeframe_type
        )
        self.timeframe_display = TimeframeConverter.format_timeframe_display(
            timeframe_value, timeframe_type
        )

        # Initialize Telegram
        self.telegram = TelegramNotifier(
            Config.TELEGRAM_BOT_TOKEN,
            Config.TELEGRAM_CHAT_ID
        )

        # Bot State
        self.product_id = None
        self.product_symbol = None
        self.last_candle_time = None
        self.price_history = deque(maxlen=self.ema_period + 100)  # Store raw prices
        self.ema_values = deque(maxlen=500)  # Keep calculated EMAs
        self.pending_order_side = None

        # Live monitoring
        self.current_price = 0
        self.current_ema = 0
        self.last_price_update = None

        # Trade tracking
        self.trade_count = 0
        self.trade_history = deque(maxlen=50)
        self.current_trade_entry = None

        # Logging
        self.log_file = f"logs/ema_bot_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        # EMA calculation constants
        self.ema_multiplier = 2.0 / (self.ema_period + 1)

        # Initialize
        self._initialize_product()
        self._load_historical_data()

        self._log(f"✅ Bot initialized successfully!", Fore.GREEN)
        self._log(f"📊 Trading {self.symbol} on {self.timeframe_display} timeframe", Fore.GREEN)
        self._log(f"⏱️  Resolution: {self.resolution} ({self.TIMEFRAME_MINUTES} minutes)", Fore.GREEN)
        print()

    def _print_header(self):
        """Print startup header"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{'🚀 EMA-200 BOT - PRODUCTION VERSION':^80}")
        print(f"{Fore.CYAN}{'='*80}\n")

    def _log(self, message, color=Fore.WHITE):
        """Log message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(f"{color}{log_msg}")

        try:
            with open(self.log_file, 'a') as f:
                f.write(log_msg + '\n')
        except:
            pass

    def _generate_signature(self, message):
        """Generate HMAC-SHA256 signature"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _get_headers(self, method, path, body=''):
        """Generate authentication headers"""
        timestamp = str(int(time.time()))
        message = method + timestamp + path + body
        signature = self._generate_signature(message)

        return {
            'api-key': self.api_key,
            'timestamp': timestamp,
            'signature': signature,
            'Content-Type': 'application/json',
            'User-Agent': 'ema-strategy-bot'
        }

    def _initialize_product(self):
        """Initialize trading product"""
        try:
            self._log(f"🔍 Searching for {self.symbol} product...", Fore.YELLOW)
            url = f"{self.base_url}/v2/products"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    products = data.get('result', [])
                    for product in products:
                        if product.get('symbol') == self.symbol:
                            self.product_id = product.get('id')
                            self.product_symbol = product.get('symbol')
                            self._log(f"✅ Product found: {self.product_symbol} (ID: {self.product_id})", Fore.GREEN)
                            return

                    self._log(f"❌ {self.symbol} not found!", Fore.RED)
        except Exception as e:
            self._log(f"❌ Error initializing product: {e}", Fore.RED)

    def _calculate_ema(self, prices, period):
        """
        Calculate EMA properly using the standard formula:
        EMA = (Close - Previous EMA) * Multiplier + Previous EMA
        where Multiplier = 2 / (Period + 1)

        First EMA uses SMA of first 'period' values
        """
        if len(prices) < period:
            return None

        # Calculate initial SMA for the first EMA value
        sma = sum(prices[:period]) / period
        ema = sma

        # Calculate EMA for remaining prices
        multiplier = 2.0 / (period + 1)
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def _load_historical_data(self):
        """Load historical candles and calculate initial EMA"""
        try:
            self._log(f"📊 Loading historical data for EMA-{self.ema_period}...", Fore.YELLOW)

            # Fetch significantly more candles for accurate calculation
            candles_needed = self.ema_period * 3
            time_range = candles_needed * self.TIMEFRAME_MINUTES * 60

            url = f"{self.base_url}/v2/history/candles"
            params = {
                'resolution': self.resolution,
                'symbol': self.product_symbol,
                'start': int(time.time()) - time_range,
                'end': int(time.time())
            }

            self._log(f"📊 Requesting {candles_needed} candles ({candles_needed * self.TIMEFRAME_MINUTES} minutes of data)...", Fore.YELLOW)

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    candles = data.get('result', [])
                    candles = sorted(candles, key=lambda x: x['time'])

                    if len(candles) >= self.ema_period:
                        closes = [float(c['close']) for c in candles]
                        self.price_history.extend(closes)

                        self._log(f"✅ Loaded {len(candles)} candles (oldest to newest)", Fore.GREEN)
                        self._log(f"📊 First candle close: ${closes[0]:,.2f}", Fore.CYAN)
                        self._log(f"📊 Last candle close: ${closes[-1]:,.2f}", Fore.CYAN)

                        self.current_ema = self._calculate_ema(closes, self.ema_period)

                        if self.current_ema:
                            self.ema_values.append(self.current_ema)
                            self._log(f"✅ Calculated EMA-{self.ema_period}: ${self.current_ema:,.2f}", Fore.GREEN)

                            diff = closes[-1] - self.current_ema
                            diff_pct = (diff / self.current_ema) * 100
                            if diff > 0:
                                self._log(f"📈 Price is ${abs(diff):,.2f} ({diff_pct:+.2f}%) ABOVE EMA", Fore.GREEN)
                            else:
                                self._log(f"📉 Price is ${abs(diff):,.2f} ({diff_pct:+.2f}%) BELOW EMA", Fore.RED)

                            if len(closes) >= self.ema_period:
                                sma = sum(closes[:self.ema_period]) / self.ema_period
                                self._log(f"🔍 Initial SMA-{self.ema_period}: ${sma:,.2f}", Fore.YELLOW)
                                self._log(f"🔍 Multiplier: {self.ema_multiplier:.6f}", Fore.YELLOW)
                        else:
                            self._log(f"❌ Failed to calculate EMA", Fore.RED)
                    else:
                        self._log(f"⚠️ Insufficient candles: {len(candles)}/{self.ema_period}", Fore.YELLOW)
        except Exception as e:
            self._log(f"❌ Error loading historical data: {e}", Fore.RED)

    def get_live_price(self):
        """Get current live price from ticker"""
        try:
            url = f"{self.base_url}/v2/tickers/{self.product_symbol}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    ticker = data.get('result', {})
                    mark_price = float(ticker.get('mark_price', 0))
                    if mark_price > 0:
                        self.current_price = mark_price
                        self.last_price_update = datetime.now()
                        return mark_price
            return None
        except Exception as e:
            return None

    def update_live_ema(self, current_price):
        """Update EMA with current live price (for display only)"""
        if self.current_ema > 0 and current_price > 0:
            live_ema = (current_price - self.current_ema) * self.ema_multiplier + self.current_ema
            return live_ema
        return self.current_ema

    def update_ema_with_new_candle(self, close_price):
        """Update EMA when a new candle closes"""
        if self.current_ema > 0:
            self.price_history.append(close_price)
            new_ema = (close_price - self.current_ema) * self.ema_multiplier + self.current_ema
            self.current_ema = new_ema
            self.ema_values.append(new_ema)
            return new_ema
        return None

    def get_orderbook(self):
        """Get current orderbook"""
        try:
            url = f"{self.base_url}/v2/l2orderbook/{self.product_symbol}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    orderbook = data.get('result', {})
                    buy_orders = orderbook.get('buy', [])
                    sell_orders = orderbook.get('sell', [])

                    if buy_orders and sell_orders:
                        return {
                            'best_bid': float(buy_orders[0]['price']),
                            'best_ask': float(sell_orders[0]['price']),
                            'spread': float(sell_orders[0]['price']) - float(buy_orders[0]['price'])
                        }
            return None
        except:
            return None

    def get_current_position(self):
        """Fetch current position from exchange"""
        try:
            path = "/v2/positions/margined"
            headers = self._get_headers("GET", path)
            url = f"{self.base_url}{path}"

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    positions = data.get('result', [])

                    for pos in positions:
                        if pos.get('product_id') == self.product_id:
                            size = float(pos.get('size', 0))

                            if size > 0:
                                return {
                                    'position': 'LONG',
                                    'size': size,
                                    'entry_price': float(pos.get('entry_price', 0)),
                                    'pnl': float(pos.get('unrealized_pnl', 0))
                                }
                            elif size < 0:
                                return {
                                    'position': 'SHORT',
                                    'size': abs(size),
                                    'entry_price': float(pos.get('entry_price', 0)),
                                    'pnl': float(pos.get('unrealized_pnl', 0))
                                }

                    return {'position': 'FLAT', 'size': 0, 'pnl': 0}

            return {'position': 'FLAT', 'size': 0, 'pnl': 0}
        except Exception as e:
            self._log(f"❌ Error getting position: {e}", Fore.RED)
            return {'position': 'FLAT', 'size': 0, 'pnl': 0}

    def get_latest_candle(self):
        """Fetch the latest fully completed candle"""
        try:
            candles_to_fetch = 10
            time_range = candles_to_fetch * self.TIMEFRAME_MINUTES * 60

            url = f"{self.base_url}/v2/history/candles"
            params = {
                'resolution': self.resolution,
                'symbol': self.product_symbol,
                'start': int(time.time()) - time_range,
                'end': int(time.time())
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    candles = data.get('result', [])
                    
                    if len(candles) >= 2:
                        candles = sorted(candles, key=lambda x: x['time'])
                        
                        current_timestamp = int(time.time())
                        current_candle_start = (current_timestamp // (self.TIMEFRAME_MINUTES * 60)) * (self.TIMEFRAME_MINUTES * 60)
                        
                        completed_candle = None
                        for i in range(len(candles) - 1, -1, -1):
                            candle_time = int(candles[i]['time'])
                            if candle_time < current_candle_start:
                                completed_candle = candles[i]
                                break
                        
                        if not completed_candle:
                            completed_candle = candles[-2]
                        
                        candle = completed_candle

                        try:
                            candle_time = datetime.fromtimestamp(int(candle['time']))
                            current_time = datetime.now()
                            time_diff = (current_time - candle_time).total_seconds() / 60

                            self._log(f"🕐 Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}", Fore.YELLOW)
                            self._log(f"🕐 Candle time: {candle_time.strftime('%Y-%m-%d %H:%M:%S')}", Fore.YELLOW)
                            self._log(f"⏱️ Candle age: {time_diff:.1f} minutes", Fore.YELLOW)

                            return {
                                'time': candle['time'],
                                'open': float(candle['open']),
                                'high': float(candle['high']),
                                'low': float(candle['low']),
                                'close': float(candle['close']),
                                'volume': float(candle['volume']),
                                'age_minutes': time_diff
                            }
                        except (ValueError, TypeError) as e:
                            self._log(f"⚠️ Error parsing candle time: {e}", Fore.YELLOW)
                            return None

            return None
        except Exception as e:
            self._log(f"❌ Error fetching candle: {e}", Fore.RED)
            return None

    def get_open_orders(self):
        """Get all open orders for the product"""
        try:
            path = "/v2/orders"
            headers = self._get_headers("GET", path)
            url = f"{self.base_url}{path}"
            
            params = {
                'product_id': self.product_id,
                'state': 'open'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    orders = data.get('result', [])
                    return orders
            return []
        except Exception as e:
            self._log(f"❌ Error fetching open orders: {e}", Fore.RED)
            return []

    def get_order_status(self, order_id):
        """Get status of a specific order"""
        try:
            path = f"/v2/orders/{order_id}"
            headers = self._get_headers("GET", path)
            url = f"{self.base_url}{path}"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    order = data.get('result', {})
                    return order
            return None
        except Exception as e:
            self._log(f"❌ Error getting order status: {e}", Fore.RED)
            return None

    def cancel_order(self, order_id):
        """Cancel a specific order"""
        try:
            path = f"/v2/orders/{order_id}"
            headers = self._get_headers("DELETE", path)
            url = f"{self.base_url}{path}"
            
            self._log(f"🚫 Cancelling order {order_id}...", Fore.YELLOW)
            
            response = requests.delete(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self._log(f"✅ Order {order_id} cancelled successfully", Fore.GREEN)
                    return True
                else:
                    error = data.get('error', 'Unknown error')
                    self._log(f"❌ Cancel failed: {error}", Fore.RED)
                    return False
            else:
                self._log(f"❌ HTTP {response.status_code}", Fore.RED)
                return False
        except Exception as e:
            self._log(f"❌ Error cancelling order: {e}", Fore.RED)
            return False

    def place_limit_order(self, side, size, price):
        """Place limit order"""
        try:
            path = "/v2/orders"

            order_data = {
                'product_id': self.product_id,
                'size': size,
                'side': side.lower(),
                'limit_price': str(price),
                'order_type': 'limit_order',
                'time_in_force': 'gtc',
                'post_only': False
            }

            body = json.dumps(order_data)
            headers = self._get_headers("POST", path, body)
            url = f"{self.base_url}{path}"

            self._log(f"📤 Placing {side.upper()} order: {size} @ ${price:,.2f}", Fore.CYAN)

            response = requests.post(url, headers=headers, data=body, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    order = data.get('result', {})
                    order_id = order.get('id')
                    self._log(f"✅ Order placed! ID: {order_id}", Fore.GREEN)
                    return {'success': True, 'order': order, 'order_id': order_id}
                else:
                    error = data.get('error', 'Unknown error')
                    self._log(f"❌ Order failed: {error}", Fore.RED)
                    return {'success': False, 'error': error}
            else:
                self._log(f"❌ HTTP {response.status_code}", Fore.RED)
                return {'success': False, 'error': response.text}

        except Exception as e:
            self._log(f"❌ Error placing order: {e}", Fore.RED)
            return {'success': False, 'error': str(e)}

    def monitor_and_replace_order(self, order_id, side, size, max_wait_seconds=15, check_interval=15):
        """Monitor an order and replace it if unfilled"""
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            order = self.get_order_status(order_id)
            
            if order:
                state = order.get('state', '')
                unfilled_size = float(order.get('unfilled_size', 0))
                
                if state == 'filled' or unfilled_size == 0:
                    self._log(f"✅ Order {order_id} filled successfully!", Fore.GREEN)
                    return True
                
                if state in ['cancelled', 'rejected']:
                    self._log(f"⚠️ Order {order_id} is {state}", Fore.YELLOW)
                    return False
                
                if elapsed >= max_wait_seconds:
                    self._log(f"⏰ Order {order_id} unfilled after {max_wait_seconds}s - replacing...", Fore.YELLOW)
                    
                    if self.cancel_order(order_id):
                        time.sleep(2)
                        orderbook = self.get_orderbook()
                        
                        if not orderbook:
                            self._log(f"❌ Could not fetch orderbook for replacement", Fore.RED)
                            return False
                        
                        new_price = orderbook['best_ask'] if side.lower() == 'buy' else orderbook['best_bid']
                        result = self.place_limit_order(side, size, new_price)
                        
                        if result.get('success'):
                            new_order_id = result.get('order_id')
                            return self.monitor_and_replace_order(new_order_id, side, size, max_wait_seconds, check_interval)
                        else:
                            return False
                    else:
                        self._log(f"❌ Failed to cancel order for replacement", Fore.RED)
                        return False
            else:
                self._log(f"⚠️ Could not fetch order status for {order_id}", Fore.YELLOW)
            
            self._log(f"⏳ Waiting {check_interval}s before next check (elapsed: {elapsed:.0f}s)...", Fore.CYAN)
            time.sleep(check_interval)

    def record_trade(self, action, side, size, price, position_type, pnl=None):
        """Record trade in history"""
        trade = TradeRecord(
            trade_id=self.trade_count,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            action=action,
            side=side,
            size=size,
            price=price,
            position_type=position_type,
            ema_value=self.current_ema,
            close_price=self.current_price
        )
        trade.pnl = pnl
        self.trade_history.append(trade)

        if action == 'OPEN':
            self.current_trade_entry = trade

    def close_position(self, current_pos):
        """Close current position with order monitoring"""
        if current_pos['position'] == 'FLAT':
            return True

        self._log(f"🔄 Closing {current_pos['position']} position (Size: {current_pos['size']})...", Fore.YELLOW)

        orderbook = self.get_orderbook()
        if not orderbook:
            self._log(f"❌ Could not fetch orderbook", Fore.RED)
            return False

        if current_pos['position'] == 'LONG':
            side = 'sell'
            price = orderbook['best_bid']
        else:
            side = 'buy'
            price = orderbook['best_ask']

        size = current_pos['size']
        result = self.place_limit_order(side, size, price)

        if result.get('success'):
            order_id = result.get('order_id')
            filled = self.monitor_and_replace_order(order_id, side, size, max_wait_seconds=15, check_interval=15)
            
            if filled:
                pnl = current_pos.get('pnl', 0)
                pnl_color = Fore.GREEN if pnl >= 0 else Fore.RED
                self._log(f"💰 Position closed! P&L: ${pnl:,.2f}", pnl_color)

                self.record_trade('CLOSE', side, size, price, current_pos['position'], pnl)
                self.trade_count += 1
                return True
            else:
                self._log(f"⚠️ Failed to fill close order", Fore.YELLOW)
                return False

        return False

    def open_position(self, direction):
        """Open new position with order monitoring"""
        self._log(f"📈 Opening {direction} position (Size: {self.lot_size})...", Fore.CYAN)

        orderbook = self.get_orderbook()
        if not orderbook:
            self._log(f"❌ Could not fetch orderbook", Fore.RED)
            return False

        self._log(f"📊 Orderbook - Bid: ${orderbook['best_bid']:,.2f} | Ask: ${orderbook['best_ask']:,.2f}", Fore.WHITE)

        if direction == 'LONG':
            side = 'buy'
            price = orderbook['best_ask']
        else:
            side = 'sell'
            price = orderbook['best_bid']

        result = self.place_limit_order(side, self.lot_size, price)

        if result.get('success'):
            order_id = result.get('order_id')
            filled = self.monitor_and_replace_order(order_id, side, self.lot_size, max_wait_seconds=15, check_interval=15)
            
            if filled:
                self.record_trade('OPEN', side, self.lot_size, price, direction)
                self.trade_count += 1
                self._log(f"✅ {direction} position opened!", Fore.GREEN)
                return True
            else:
                self._log(f"⚠️ Failed to fill open order", Fore.YELLOW)
                return False

        return False

    def display_live_status(self):
        """Display live monitoring dashboard"""
        live_price = self.get_live_price()
        live_ema_estimate = self.current_ema

        if live_price:
            live_ema_estimate = self.update_live_ema(live_price)

        pos = self.get_current_position()

        print("\n" * 2)
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{'📊 LIVE MONITORING DASHBOARD':^80}")
        print(f"{Fore.CYAN}{'='*80}")

        print(f"{Fore.WHITE}⏰ Time:           {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.WHITE}💰 Live Price:     ${self.current_price:,.2f}")
        print(f"{Fore.GREEN}📊 EMA-{self.ema_period} (Last):  ${self.current_ema:,.2f}")
        print(f"{Fore.YELLOW}📊 EMA-{self.ema_period} (Live):  ${live_ema_estimate:,.2f}")

        diff = self.current_price - self.current_ema
        diff_pct = (diff / self.current_ema) * 100 if self.current_ema != 0 else 0
        if diff > 0:
            print(f"{Fore.GREEN}📈 Price vs EMA:   +${abs(diff):,.2f} ({diff_pct:+.2f}%) ABOVE")
        else:
            print(f"{Fore.RED}📉 Price vs EMA:   -${abs(diff):,.2f} ({diff_pct:+.2f}%) BELOW")

        print(f"{Fore.WHITE}💼 Position:       {pos['position']}")
        if pos['position'] != 'FLAT':
            pnl_color = Fore.GREEN if pos.get('pnl', 0) >= 0 else Fore.RED
            print(f"{Fore.WHITE}📦 Size:           {pos['size']}")
            print(f"{Fore.WHITE}💵 Entry:          ${pos.get('entry_price', 0):,.2f}")
            print(f"{pnl_color}💰 P&L:            ${pos.get('pnl', 0):,.2f}")

        print(f"{Fore.WHITE}🔢 Total Trades:   {self.trade_count}")
        print(f"{Fore.WHITE}⏱️  Timeframe:      {self.timeframe_display}")

        print(f"{Fore.CYAN}{'='*80}\n")

        self.display_recent_trades()

    def display_recent_trades(self, count=5):
        """Display recent trade history"""
        if not self.trade_history:
            print(f"{Fore.YELLOW}📝 No trades yet\n")
            return

        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{'📝 RECENT TRADES':^80}")
        print(f"{Fore.CYAN}{'='*80}")

        recent = list(self.trade_history)[-count:]
        for trade in reversed(recent):
            color = Fore.GREEN if trade.action == 'OPEN' else Fore.YELLOW
            if trade.pnl is not None:
                pnl_color = Fore.GREEN if trade.pnl >= 0 else Fore.RED
                pnl_str = f"{pnl_color}P&L: ${trade.pnl:,.2f}"
            else:
                pnl_str = f"{Fore.WHITE}Status: Open"

            print(f"{color}#{trade.trade_id:03d} | {trade.timestamp} | {trade.action:5s}")
            print(f"{Fore.WHITE}     {trade.side.upper():4s} {trade.size} @ ${trade.price:,.2f} | {pnl_str}")

        print(f"{Fore.CYAN}{'='*80}\n")

    def execute_signal(self, signal):
        """Execute trading signal immediately"""
        self._log(f"\n{'='*80}", Fore.MAGENTA)
        self._log(f"⚡ EXECUTING {signal} SIGNAL", Fore.MAGENTA)
        self._log(f"{'='*80}", Fore.MAGENTA)

        current_pos = self.get_current_position()

        if signal != current_pos['position']:
            if current_pos['position'] != 'FLAT':
                self._log(f"🔄 Closing existing {current_pos['position']} position first...", Fore.YELLOW)
                if self.close_position(current_pos):
                    time.sleep(3)
                else:
                    self._log(f"⚠️ Failed to close position, proceeding anyway", Fore.YELLOW)
                    time.sleep(2)

            self.open_position(signal)
        else:
            self._log(f"✅ Already in {signal} position - no action needed", Fore.GREEN)

        self._log(f"{'='*80}\n", Fore.MAGENTA)

    def run(self):
        """Main bot loop"""
        self._log(f"\n{'='*80}", Fore.CYAN)
        self._log(f"🤖 BOT STARTED", Fore.CYAN)
        self._log(f"{'='*80}\n", Fore.CYAN)

        loop_counter = 0

        while True:
            try:
                candle = self.get_latest_candle()

                if candle and self.last_candle_time != candle['time']:
                    self.last_candle_time = candle['time']
                    self._log(f"🆕 New candle detected!", Fore.CYAN)
                    self._log(f"📊 Candle Close: ${candle['close']:,.2f}", Fore.WHITE)

                    new_ema = self.update_ema_with_new_candle(candle['close'])

                    if new_ema:
                        self._log(f"📊 Updated EMA-{self.ema_period}: ${new_ema:,.2f}", Fore.GREEN)

                        if candle['close'] > new_ema:
                            signal = 'LONG'
                            self._log(f"📊 Close ${candle['close']:,.2f} > EMA ${new_ema:,.2f} → LONG", Fore.GREEN)
                        else:
                            signal = 'SHORT'
                            self._log(f"📊 Close ${candle['close']:,.2f} < EMA ${new_ema:,.2f} → SHORT", Fore.RED)

                        self.execute_signal(signal)

                if loop_counter % 3 == 0:
                    self.display_live_status()

                loop_counter += 1
                time.sleep(10)

            except KeyboardInterrupt:
                self._log(f"\n🛑 Bot stopped by user", Fore.YELLOW)
                self._log(f"📊 Total trades: {self.trade_count}", Fore.CYAN)
                self.display_recent_trades(10)
                break
            except Exception as e:
                self._log(f"❌ Error in main loop: {e}", Fore.RED)
                time.sleep(10)


if __name__ == "__main__":
    try:
        bot = EMAStrategyBot()
        bot.run()
    except Exception as e:
        print(f"{Fore.RED}❌ Fatal error: {e}")
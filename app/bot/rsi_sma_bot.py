#!/usr/bin/env python3
"""
Accurate RSI-SMA Trading Bot - DOCKER VERSION
Optimized for containerized deployment
"""
import os
import sys
import time

# Add current directory to path for imports
sys.path.append('/app')

try:
    import requests
    import hmac
    import hashlib
    import json
    from datetime import datetime, timedelta
    from collections import deque
    from config_rsi_sma  import Config
    from colorama import init, Fore, Style
    import pytz
    from telegram_notifier import TelegramNotifier
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure all dependencies are installed in requirements.txt")
    sys.exit(1)

init(autoreset=True)


class TradeRecord:
    """Record for tracking individual trades"""
    def __init__(self, trade_id, timestamp, action, side, size, price, position_type, rsi_value, sma_value):
        self.trade_id = trade_id
        self.timestamp = timestamp
        self.action = action
        self.side = side
        self.size = size
        self.price = price
        self.position_type = position_type
        self.rsi_value = rsi_value
        self.sma_value = sma_value
        self.pnl = None


class AccurateRSISMABot:
    """Accurate RSI-SMA Strategy matching TradingView calculations"""
    
    def __init__(self):
        self.base_url = Config.get_base_url()
        self.api_key = Config.DELTA_API_KEY
        self.api_secret = Config.DELTA_API_SECRET
        
        # STRATEGY PARAMETERS
        self.symbol = Config.SYMBOL
        self.lot_size = Config.LOT_SIZE
        
        # Indicator settings
        self.rsi_period = Config.RSI_PERIOD
        self.sma_period = Config.SMA_PERIOD
        self.timeframe_minutes = Config.TIMEFRAME_1M
        
        # Generate resolution string
        if self.timeframe_minutes >= 60:
            self.resolution = f"{int(self.timeframe_minutes / 60)}h"
            self.timeframe_display = f"{int(self.timeframe_minutes / 60)}h"
        else:
            self.resolution = f"{self.timeframe_minutes}m"
            self.timeframe_display = f"{self.timeframe_minutes}m"
        
        # TradingView settings
        self.tv_symbol = Config.TV_SYMBOL
        
        # TIMEZONE
        self.timezone = pytz.timezone('Asia/Kolkata')
        self.utc_tz = pytz.UTC
        
        # Print header
        self._print_header()
        
        # Bot State
        self.product_id = None
        self.product_symbol = None
        self.current_position = 'FLAT'
        self.last_candle_time = None
        
        # Current price
        self.current_price = 0
        
        # Candle close tracking
        self.candle_closes = deque(maxlen=self.rsi_period + 100)
        self.candle_timestamps = deque(maxlen=self.rsi_period + 100)
        
        # RSI Calculation - Wilder's Method (matches TradingView)
        self.current_rsi = 0
        self.prev_rsi = 0
        self.avg_gain = None
        self.avg_loss = None
        self.rsi_initialized = False
        
        # SMA of RSI
        self.rsi_history = deque(maxlen=self.sma_period)
        self.current_sma = 0
        self.prev_sma = 0
        
        # Trade tracking
        self.trade_count = 0
        self.trade_history = deque(maxlen=50)
        
        # Crossover detection
        self.last_cross_direction = None
        self.pending_signal = None
        
        # Wallet balance tracking
        self.wallet_balance = 0
        self.available_balance = 0
        self.margin_used = 0
        
        # Performance tracking
        self.total_pnl = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Logging
        self.log_file = f"logs/accurate_rsi_sma_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Initialize
        self._initialize_product()
        self._load_historical_candles()
        
        # Test API
        self.test_api_connectivity()
        self._update_wallet_balance()
        
        self._log(f"✅ Bot initialized - RSI/SMA calculated on completed candles only!", Fore.GREEN)
        print()
    
    def _print_header(self):
        """Print startup header"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{f'🎯 ACCURATE RSI-SMA BOT - TRADINGVIEW MATCH':^80}")
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}{f'✅ RSI({self.rsi_period}) on {self.timeframe_display.upper()} COMPLETED candles':^80}")
        print(f"{Fore.YELLOW}{f'✅ SMA({self.sma_period}) of RSI':^80}")
        print(f"{Fore.YELLOW}{f'✅ Updates ONLY when candles complete':^80}")
        print(f"{Fore.GREEN}{'✅ Matches TradingView exactly':^80}")
        print(f"{Fore.MAGENTA}{'✅ No live price interference':^80}")
        print(f"{Fore.CYAN}{'='*80}\n")
    
    def _log(self, message, color=Fore.WHITE):
        """Log message with IST timestamp"""
        ist_now = datetime.now(self.timezone)
        timestamp = ist_now.strftime('%Y-%m-%d %H:%M:%S IST')
        log_msg = f"[{timestamp}] {message}"
        
        # Print to console with color (will be captured by Docker logs)
        print(f"{color}{log_msg}", flush=True)
        
        # Send to WebSocket via telegram notifier
        if self.telegram:
            self.telegram.send_message(log_msg)
    
    def _log_detailed(self, title, data_dict, color=Fore.CYAN):
        """Log detailed information"""
        self._log(f"\n{'─'*50}", color)
        self._log(f"📊 {title}", color)
        self._log(f"{'─'*50}", color)
        for key, value in data_dict.items():
            self._log(f"   {key}: {value}", Fore.WHITE)
        self._log(f"{'─'*50}", color)
    
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
            'Content-Type': 'application/json'
        }
    
    def test_api_connectivity(self):
        """Test API connectivity"""
        try:
            path = "/v2/wallet/balances"
            headers = self._get_headers("GET", path)
            url = f"{self.base_url}{path}"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self._log("✅ API connectivity: SUCCESS", Fore.GREEN)
                    return True
            return False
        except:
            return False
    
    def _update_wallet_balance(self):
        """Update wallet balance"""
        try:
            path = "/v2/wallet/balances"
            headers = self._get_headers("GET", path)
            url = f"{self.base_url}{path}"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    balances = data.get('result', [])
                    
                    for balance in balances:
                        asset_symbol = balance.get('asset_symbol')
                        if asset_symbol == 'USDT' or 'USDT' in str(asset_symbol):
                            self.wallet_balance = float(balance.get('balance', 0))
                            self.available_balance = float(balance.get('available_balance', 0))
                            self.margin_used = self.wallet_balance - self.available_balance
                            return True
            return False
        except:
            return False
    
    def _initialize_product(self):
        """Initialize trading product"""
        try:
            self._log(f"🔍 Initializing {self.symbol}...", Fore.YELLOW)
            url = f"{self.base_url}/v2/products"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    for product in data.get('result', []):
                        if product.get('symbol') == self.symbol:
                            self.product_id = product.get('id')
                            self.product_symbol = product.get('symbol')
                            self._log(f"✅ Product: {self.product_symbol}", Fore.GREEN)
                            return
            
            self.product_symbol = self.symbol
        except:
            self.product_symbol = self.symbol
    
    def _get_last_completed_candle_time(self):
        """Get timestamp of last COMPLETED candle"""
        now = datetime.now(self.utc_tz)
        minutes = (now.minute // self.timeframe_minutes) * self.timeframe_minutes
        last_boundary = now.replace(minute=minutes, second=0, microsecond=0)
        last_completed = last_boundary - timedelta(minutes=self.timeframe_minutes)
        return int(last_completed.timestamp())
    
    def _fetch_binance_candles(self, num_candles=100):
        """Fetch completed candles from Binance"""
        try:
            binance_symbol = self.tv_symbol.replace('BINANCE:', '').replace('USDT', 'USDT')
            url = f"https://api.binance.com/api/v3/klines"
            
            params = {
                'symbol': binance_symbol,
                'interval': self.resolution,
                'limit': num_candles + 10
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                klines = response.json()
                
                candles = []
                for k in klines:
                    candle = {
                        'time': int(k[0]) // 1000,
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5])
                    }
                    candles.append(candle)
                
                # Filter only completed candles
                last_completed_time = self._get_last_completed_candle_time()
                completed_candles = []
                
                for candle in candles:
                    dt = datetime.fromtimestamp(candle['time'], self.utc_tz)
                    if dt.minute % self.timeframe_minutes == 0 and dt.second == 0:
                        if candle['time'] <= last_completed_time:
                            completed_candles.append(candle)
                
                completed_candles.sort(key=lambda x: x['time'])
                return completed_candles[-num_candles:] if len(completed_candles) > num_candles else completed_candles
            
            return []
        except Exception as e:
            self._log(f"❌ Binance fetch error: {e}", Fore.RED)
            return []
    
    def _load_historical_candles(self):
        """Load historical COMPLETED candles for initialization"""
        try:
            required_candles = self.rsi_period + self.sma_period + 20
            self._log(f"🔧 Loading {required_candles} completed {self.timeframe_display} candles...", Fore.YELLOW)
            
            candles = self._fetch_binance_candles(required_candles)
            
            if len(candles) >= self.rsi_period + self.sma_period:
                closes = []
                timestamps = []
                
                for candle in candles:
                    closes.append(float(candle['close']))
                    timestamps.append(candle['time'])
                
                self.candle_closes = deque(closes, maxlen=self.rsi_period + 100)
                self.candle_timestamps = deque(timestamps, maxlen=self.rsi_period + 100)
                self.last_candle_time = timestamps[-1]
                
                # Calculate RSI for each historical point
                rsi_values = []
                for i in range(self.rsi_period + 1, len(closes) + 1):
                    subset = closes[:i]
                    if i == self.rsi_period + 1:
                        self.rsi_initialized = False
                        self.avg_gain = None
                        self.avg_loss = None
                    rsi = self.calculate_rsi_wilder(subset)
                    if rsi is not None:
                        rsi_values.append(rsi)
                
                self.rsi_history = deque(rsi_values, maxlen=self.sma_period)
                
                self.prev_rsi = rsi_values[-2] if len(rsi_values) >= 2 else rsi_values[-1]
                self.current_rsi = rsi_values[-1]
                
                if len(self.rsi_history) >= self.sma_period:
                    self.prev_sma = self.calculate_sma(list(self.rsi_history)[:-1])
                    self.current_sma = self.calculate_sma(self.rsi_history)
                
                last_candle_ist = datetime.fromtimestamp(timestamps[-1], self.timezone)
                
                init_details = {
                    "Candles Loaded": f"{len(candles)} completed candles",
                    "Timeframe": self.timeframe_display,
                    "Last Candle Time": last_candle_ist.strftime('%Y-%m-%d %H:%M IST'),
                    f"RSI({self.rsi_period})": f"{self.current_rsi:.2f}",
                    f"SMA({self.sma_period})": f"{self.current_sma:.2f}",
                    "State": "RSI ABOVE SMA (Bullish)" if self.current_rsi > self.current_sma else "RSI BELOW SMA (Bearish)",
                    "Data Source": "Binance (matches TradingView)"
                }
                self._log_detailed("✅ INITIALIZATION COMPLETE", init_details, Fore.GREEN)
                
            else:
                self._log(f"❌ Insufficient candles: {len(candles)}", Fore.RED)
        except Exception as e:
            self._log(f"❌ Error loading candles: {e}", Fore.RED)
    
    def calculate_rsi_wilder(self, closes):
        """Calculate RSI using Wilder's RMA - EXACT TradingView match"""
        if len(closes) < self.rsi_period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            elif change < 0:
                gains.append(0)
                losses.append(abs(change))
            else:
                gains.append(0)
                losses.append(0)
        
        if len(gains) < self.rsi_period:
            return None
        
        if not self.rsi_initialized:
            self.avg_gain = sum(gains[:self.rsi_period]) / self.rsi_period
            self.avg_loss = sum(losses[:self.rsi_period]) / self.rsi_period
            self.rsi_initialized = True
            
            for i in range(self.rsi_period, len(gains)):
                self.avg_gain = ((self.avg_gain * (self.rsi_period - 1)) + gains[i]) / self.rsi_period
                self.avg_loss = ((self.avg_loss * (self.rsi_period - 1)) + losses[i]) / self.rsi_period
        else:
            current_gain = gains[-1]
            current_loss = losses[-1]
            self.avg_gain = ((self.avg_gain * (self.rsi_period - 1)) + current_gain) / self.rsi_period
            self.avg_loss = ((self.avg_loss * (self.rsi_period - 1)) + current_loss) / self.rsi_period
        
        if self.avg_loss == 0:
            rsi = 100
        else:
            rs = self.avg_gain / self.avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def calculate_sma(self, values):
        """Calculate SMA"""
        if len(values) < self.sma_period:
            return None
        
        recent_values = list(values)[-self.sma_period:]
        sma = sum(recent_values) / len(recent_values)
        return round(sma, 2)
    
    def check_for_new_candle(self):
        """Check if new candle completed"""
        try:
            last_completed_time = self._get_last_completed_candle_time()
            
            if last_completed_time != self.last_candle_time:
                candles = self._fetch_binance_candles(1)
                if candles and candles[0]['time'] == last_completed_time:
                    return candles[0]
            
            return None
        except:
            return None
    
    def update_indicators_with_new_candle(self, candle):
        """Update RSI and SMA with new COMPLETED candle"""
        new_close = float(candle['close'])
        candle_time = candle['time']
        
        self.prev_rsi = self.current_rsi
        self.prev_sma = self.current_sma
        
        self.candle_closes.append(new_close)
        self.candle_timestamps.append(candle_time)
        self.last_candle_time = candle_time
        
        # Recalculate RSI
        self.current_rsi = self.calculate_rsi_wilder(list(self.candle_closes))
        
        if self.current_rsi is not None:
            self.rsi_history.append(self.current_rsi)
            if len(self.rsi_history) >= self.sma_period:
                self.current_sma = self.calculate_sma(self.rsi_history)
        
        candle_time_ist = datetime.fromtimestamp(candle_time, self.timezone)
        
        candle_details = {
            "Time": candle_time_ist.strftime('%Y-%m-%d %H:%M IST'),
            "Close Price": f"${new_close:,.2f}",
            f"RSI({self.rsi_period})": f"{self.prev_rsi:.2f} → {self.current_rsi:.2f}",
            f"SMA({self.sma_period})": f"{self.prev_sma:.2f} → {self.current_sma:.2f}",
            "RSI Change": f"{self.current_rsi - self.prev_rsi:+.2f}",
            "SMA Change": f"{self.current_sma - self.prev_sma:+.2f}",
            "Position": "RSI ABOVE SMA" if self.current_rsi > self.current_sma else "RSI BELOW SMA"
        }
        self._log_detailed(f"🆕 {self.timeframe_display.upper()} CANDLE COMPLETED", candle_details, Fore.GREEN)
        
        self.detect_crossover()
    
    def detect_crossover(self):
        """Detect RSI-SMA crossover"""
        if self.prev_rsi == 0 or self.prev_sma == 0:
            return
        
        pos = self.get_current_position()
        
        # Bullish crossover
        if self.prev_rsi <= self.prev_sma and self.current_rsi > self.current_sma:
            if pos['position'] == 'LONG':
                self._log(f"✅ Already LONG - ignoring bullish signal", Fore.YELLOW)
                return
            
            cross_details = {
                "Type": "🟢 BULLISH CROSSOVER",
                "RSI": f"{self.prev_rsi:.2f} → {self.current_rsi:.2f}",
                "SMA": f"{self.prev_sma:.2f} → {self.current_sma:.2f}",
                "Status": "RSI crossed ABOVE SMA",
                "Action": "Executing LONG trade"
            }
            self._log_detailed("🎯 CROSSOVER DETECTED", cross_details, Fore.GREEN)
            self.pending_signal = 'LONG'
        
        # Bearish crossover
        elif self.prev_rsi >= self.prev_sma and self.current_rsi < self.current_sma:
            if pos['position'] == 'SHORT':
                self._log(f"✅ Already SHORT - ignoring bearish signal", Fore.YELLOW)
                return
            
            cross_details = {
                "Type": "🔴 BEARISH CROSSOVER",
                "RSI": f"{self.prev_rsi:.2f} → {self.current_rsi:.2f}",
                "SMA": f"{self.prev_sma:.2f} → {self.current_sma:.2f}",
                "Status": "RSI crossed BELOW SMA",
                "Action": "Executing SHORT trade"
            }
            self._log_detailed("🎯 CROSSOVER DETECTED", cross_details, Fore.RED)
            self.pending_signal = 'SHORT'
    
    def get_live_price(self):
        """Get current live price for display only"""
        try:
            binance_symbol = self.tv_symbol.replace('BINANCE:', '').replace('USDT', 'USDT')
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                price = float(data.get('price', 0))
                self.current_price = price
                return price
            return None
        except:
            return None
    
    def get_current_position(self):
        """Get current position"""
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
            
            return {'position': 'FLAT', 'size': 0}
        except:
            return {'position': 'FLAT', 'size': 0}
    
    def get_orderbook(self):
        """Get orderbook"""
        try:
            binance_symbol = self.tv_symbol.replace('BINANCE:', '').replace('USDT', 'USDT')
            url = f"https://api.binance.com/api/v3/depth?symbol={binance_symbol}&limit=5"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                bids = data.get('bids', [])
                asks = data.get('asks', [])
                
                if bids and asks:
                    return {
                        'best_bid': float(bids[0][0]),
                        'best_ask': float(asks[0][0]),
                        'spread': float(asks[0][0]) - float(bids[0][0])
                    }
            return None
        except:
            return None
    
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
            
            response = requests.post(url, headers=headers, data=body, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {'success': True, 'order': data.get('result', {})}
            
            return {'success': False}
        except:
            return {'success': False}
    
    def execute_trade(self):
        """Execute pending trade"""
        if not self.pending_signal:
            return
        
        signal = self.pending_signal
        self.pending_signal = None
        
        self._update_wallet_balance()
        pos = self.get_current_position()
        orderbook = self.get_orderbook()
        
        if not orderbook:
            self._log(f"❌ No orderbook", Fore.RED)
            return
        
        # Close existing position
        if pos['position'] != 'FLAT':
            close_side = 'sell' if pos['position'] == 'LONG' else 'buy'
            close_price = orderbook['best_bid'] if close_side == 'sell' else orderbook['best_ask']
            
            self._log(f"🔄 Closing {pos['position']} position...", Fore.YELLOW)
            close_result = self.place_limit_order(close_side, pos['size'], close_price)
            
            if close_result['success']:
                self._log(f"✅ Position closed", Fore.GREEN)
                time.sleep(2)
            else:
                self._log(f"❌ Failed to close", Fore.RED)
                return
        
        # Open new position
        entry_side = 'buy' if signal == 'LONG' else 'sell'
        entry_price = orderbook['best_ask'] if entry_side == 'buy' else orderbook['best_bid']
        
        self._log(f"📈 Opening {signal} position...", Fore.CYAN)
        entry_result = self.place_limit_order(entry_side, self.lot_size, entry_price)
        
        if entry_result['success']:
            entry_details = {
                "Action": f"{signal} OPENED",
                "Price": f"${entry_price:,.2f}",
                "Size": f"{self.lot_size} contracts",
                "RSI": f"{self.current_rsi:.2f}",
                "SMA": f"{self.current_sma:.2f}"
            }
            self._log_detailed("✅ TRADE EXECUTED", entry_details, Fore.GREEN)
            self.trade_count += 1
        else:
            self._log(f"❌ Failed to open {signal}", Fore.RED)
    
    def print_status(self):
        """Print current status"""
        pos = self.get_current_position()
        price = self.get_live_price()
        
        if self.last_candle_time:
            last_candle_ist = datetime.fromtimestamp(self.last_candle_time, self.timezone)
            last_candle_str = last_candle_ist.strftime('%H:%M:%S IST')
        else:
            last_candle_str = "N/A"
        
        status_details = {
            "Live Price": f"${price:,.2f}" if price else "N/A",
            "Last Candle": last_candle_str,
            f"RSI({self.rsi_period})": f"{self.current_rsi:.2f}",
            f"SMA({self.sma_period})": f"{self.current_sma:.2f}",
            "RSI vs SMA": "ABOVE (Bullish)" if self.current_rsi > self.current_sma else "BELOW (Bearish)",
            "Position": pos['position'],
            "Size": f"{pos['size']} contracts" if pos['position'] != 'FLAT' else "N/A",
            "PnL": f"${pos['pnl']:,.2f}" if pos['position'] != 'FLAT' else "N/A",
            "Wallet": f"${self.wallet_balance:,.2f}",
            "Total Trades": self.trade_count
        }
        
        self._log_detailed("📊 BOT STATUS", status_details, Fore.CYAN)
    
    def run(self):
        """Main bot loop"""
        startup_details = {
            "Symbol": self.symbol,
            "Strategy": f"RSI-SMA Crossover (TradingView Match)",
            "RSI Period": self.rsi_period,
            "SMA Period": self.sma_period,
            "Timeframe": self.timeframe_display,
            "Lot Size": f"{self.lot_size} contracts",
            "Current RSI": f"{self.current_rsi:.2f}",
            "Current SMA": f"{self.current_sma:.2f}",
            "Status": "ACTIVE - Monitoring completed candles only"
        }
        self._log_detailed("🚀 BOT STARTED", startup_details, Fore.GREEN)
        
        loop_count = 0
        
        try:
            while True:
                loop_count += 1
                
                # Check for new COMPLETED candle
                new_candle = self.check_for_new_candle()
                if new_candle:
                    self.update_indicators_with_new_candle(new_candle)
                
                # Execute pending trades
                if self.pending_signal:
                    self.execute_trade()
                
                # Status update every 20 iterations
                if loop_count % 20 == 0:
                    self.print_status()
                
                # Update live price for display
                self.get_live_price()
                
                time.sleep(5)  # Check every 5 seconds
                
        except KeyboardInterrupt:
            shutdown_details = {
                "Total Trades": self.trade_count,
                "Final RSI": f"{self.current_rsi:.2f}",
                "Final SMA": f"{self.current_sma:.2f}",
                "Position": self.get_current_position()['position'],
                "Wallet": f"${self.wallet_balance:,.2f}",
                "Status": "STOPPED BY USER"
            }
            self._log_detailed("🛑 BOT STOPPED", shutdown_details, Fore.YELLOW)


if __name__ == "__main__":
    bot = AccurateRSISMABot()
    bot.run()
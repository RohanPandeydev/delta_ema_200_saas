"""
RSI-SMA Trading Bot - TradingView Exact Match with Telegram Notifications
===========================================================================
✅ Wilder's smoothing (RMA) - exact TradingView method
✅ Only completed candles used
✅ Proper initialization with historical data
✅ Accurate crossover detection
✅ Real-time Telegram notifications
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from collections import deque
from config import Config
from colorama import init, Fore, Style
import pytz
from telegram_notifier import TelegramNotifier

init(autoreset=True)


class TradingViewRSI:
    """
    Exact TradingView RSI Calculator
    Uses Wilder's smoothing method (RMA)
    """
    
    def __init__(self, period=14):
        self.period = period
        self.avg_gain = 0
        self.avg_loss = 0
        self.initialized = False
        self.historical_gains = []
        self.historical_losses = []
    
    def initialize(self, prices):
        """
        Initialize RSI with historical price data
        
        Args:
            prices: List of close prices (minimum period+1 required)
        
        Returns:
            List of RSI values starting from index period
        """
        if len(prices) < self.period + 1:
            return []
        
        # Calculate all price changes
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [max(c, 0) for c in changes]
        losses = [max(-c, 0) for c in changes]
        
        # First average: Simple average of first period values
        self.avg_gain = sum(gains[:self.period]) / self.period
        self.avg_loss = sum(losses[:self.period]) / self.period
        
        # Store for recalculation if needed
        self.historical_gains = gains[:self.period]
        self.historical_losses = losses[:self.period]
        
        # Calculate RSI series using Wilder's smoothing
        rsi_values = []
        
        for i in range(self.period, len(gains)):
            # Wilder's smoothing
            self.avg_gain = (self.avg_gain * (self.period - 1) + gains[i]) / self.period
            self.avg_loss = (self.avg_loss * (self.period - 1) + losses[i]) / self.period
            
            # Calculate RSI
            if self.avg_loss == 0:
                rsi = 100.0
            else:
                rs = self.avg_gain / self.avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
            
            rsi_values.append(round(rsi, 2))
        
        self.initialized = True
        return rsi_values
    
    def update(self, new_price, prev_price):
        """
        Update RSI with new price (for new completed candle)
        
        Args:
            new_price: New close price
            prev_price: Previous close price
        
        Returns:
            Updated RSI value
        """
        if not self.initialized:
            raise ValueError("RSI must be initialized first")
        
        # Calculate change
        change = new_price - prev_price
        gain = max(change, 0)
        loss = max(-change, 0)
        
        # Wilder's smoothing
        self.avg_gain = (self.avg_gain * (self.period - 1) + gain) / self.period
        self.avg_loss = (self.avg_loss * (self.period - 1) + loss) / self.period
        
        # Calculate RSI
        if self.avg_loss == 0:
            return 100.0
        
        rs = self.avg_gain / self.avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        
        return round(rsi, 2)
    
    def get_current_state(self):
        """Get current internal state for debugging"""
        return {
            'initialized': self.initialized,
            'avg_gain': round(self.avg_gain, 6),
            'avg_loss': round(self.avg_loss, 6),
            'rs': round(self.avg_gain / self.avg_loss, 6) if self.avg_loss > 0 else float('inf')
        }


class SimpleMovingAverage:
    """Simple Moving Average calculator"""
    
    @staticmethod
    def calculate(values, period):
        """Calculate SMA"""
        if len(values) < period:
            return None
        recent = list(values)[-period:]
        return round(sum(recent) / len(recent), 2)


class AccurateRSISMABot:
    """RSI-SMA Trading Bot with TradingView-exact calculations and Telegram notifications"""
    
    def __init__(self):
        self.base_url = Config.get_base_url()
        self.api_key = Config.DELTA_API_KEY
        self.api_secret = Config.DELTA_API_SECRET
        
        # STRATEGY PARAMETERS
        self.symbol = Config.SYMBOL
        self.lot_size = Config.ORDER_SIZE
        
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
        
        # Initialize Telegram Notifier
        self.telegram = TelegramNotifier(
            bot_token=getattr(Config, 'TELEGRAM_BOT_TOKEN', ''),
            chat_id=getattr(Config, 'TELEGRAM_CHAT_ID', '')
        )
        
        # Connection management
        self._setup_sessions()
        self.last_successful_api_call = time.time()
        self.api_failure_count = 0
        self.max_consecutive_failures = 5
        
        # Print header
        self._print_header()
        
        # Bot State
        self.product_id = None
        self.product_symbol = None
        self.current_position = 'FLAT'
        self.last_candle_time = None
        
        # Current price
        self.current_price = 0
        
        # Price history
        self.price_history = deque(maxlen=self.rsi_period + 100)
        self.candle_timestamps = deque(maxlen=self.rsi_period + 100)
        
        # RSI Calculator - TradingView exact
        self.rsi_calculator = TradingViewRSI(period=self.rsi_period)
        self.current_rsi = 0
        self.prev_rsi = 0
        
        # SMA of RSI
        self.rsi_history = deque(maxlen=self.sma_period + 10)
        self.current_sma = 0
        self.prev_sma = 0
        
        # Trade tracking
        self.trade_count = 0
        self.trade_history = deque(maxlen=50)
        
        # Crossover detection
        self.pending_signal = None
        
        # Position tracking for P&L
        self.last_position_entry = None
        self.last_position_size = 0
        
        # Wallet balance
        self.wallet_balance = 0
        self.available_balance = 0
        self.margin_used = 0
        
        # Performance tracking
        self.total_pnl = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Logging
        self.log_file = f"logs/rsi_sma_accurate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Initialize
        self._initialize_product()
        self._load_historical_candles()
        self._fetch_wallet_balance()
        
        self._log(f"✅ Bot initialized - TradingView exact match!", Fore.GREEN)
        
        # Send Telegram notification for bot start
        if self.telegram.enabled:
            self.telegram.notify_bot_start(
                symbol=self.symbol,
                timeframe=self.timeframe_display,
                rsi_period=self.rsi_period,
                sma_period=self.sma_period,
                lot_size=self.lot_size
            )
        
        print()
    
    def _setup_sessions(self):
        """Setup HTTP sessions with retry logic"""
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        self.delta_session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.delta_session.mount("http://", adapter)
        self.delta_session.mount("https://", adapter)
        
        self.binance_session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.binance_session.mount("http://", adapter)
        self.binance_session.mount("https://", adapter)
        
        self._log("✅ HTTP sessions configured", Fore.GREEN)
    
    def _reset_sessions(self):
        """Reset HTTP sessions on connection issues"""
        self._log("🔄 Resetting HTTP sessions...", Fore.YELLOW)
        try:
            self.delta_session.close()
            self.binance_session.close()
        except:
            pass
        
        time.sleep(2)
        self._setup_sessions()
        self._log("✅ Sessions reset complete", Fore.GREEN)
    
    def _check_connection_health(self):
        """Check if connection is healthy"""
        time_since_last_success = time.time() - self.last_successful_api_call
        
        if time_since_last_success > 300:
            self._log(f"⚠️ No successful API call for {time_since_last_success:.0f}s, resetting", Fore.YELLOW)
            self._reset_sessions()
            self.api_failure_count = 0
            return False
        
        if self.api_failure_count >= self.max_consecutive_failures:
            self._log(f"⚠️ {self.api_failure_count} consecutive failures, resetting", Fore.YELLOW)
            self._reset_sessions()
            self.api_failure_count = 0
            return False
        
        return True
    
    def _safe_api_call(self, func, *args, max_retries=3, **kwargs):
        """Wrapper for API calls with retry logic"""
        for attempt in range(max_retries):
            try:
                result = func(*args, **kwargs)
                self.last_successful_api_call = time.time()
                self.api_failure_count = 0
                return result
            except requests.exceptions.Timeout as e:
                self._log(f"⚠️ Timeout {attempt+1}/{max_retries}: {str(e)[:100]}", Fore.YELLOW)
                self.api_failure_count += 1
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
            except requests.exceptions.ConnectionError as e:
                self._log(f"⚠️ Connection error {attempt+1}/{max_retries}", Fore.YELLOW)
                self.api_failure_count += 1
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    if attempt == max_retries - 2:
                        self._reset_sessions()
            except Exception as e:
                self._log(f"❌ API error: {str(e)[:150]}", Fore.RED)
                self.api_failure_count += 1
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def _print_header(self):
        """Print startup header"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{f'🎯 RSI-SMA BOT - TRADINGVIEW EXACT MATCH + TELEGRAM':^80}")
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}{f'✅ RSI({self.rsi_period}) - Wilders RMA':^80}")
        print(f"{Fore.YELLOW}{f'✅ SMA({self.sma_period}) of RSI':^80}")
        print(f"{Fore.YELLOW}{f'✅ Completed candles only':^80}")
        print(f"{Fore.GREEN}{'✅ Verified TradingView accuracy':^80}")
        print(f"{Fore.GREEN}{'📱 Telegram notifications enabled':^80}")
        print(f"{Fore.CYAN}{'='*80}\n")
    
    def _log(self, message, color=Fore.WHITE):
        """Log message with IST timestamp"""
        ist_now = datetime.now(self.timezone)
        timestamp = ist_now.strftime('%Y-%m-%d %H:%M:%S IST')
        log_msg = f"[{timestamp}] {message}"
        print(f"{color}{log_msg}")
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_msg + '\n')
        except:
            pass
    
    def _log_detailed(self, title, data_dict, color=Fore.CYAN):
        """Log detailed information"""
        self._log(f"\n{'─'*60}", color)
        self._log(f"📊 {title}", color)
        self._log(f"{'─'*60}", color)
        for key, value in data_dict.items():
            self._log(f"   {key}: {value}", Fore.WHITE)
        self._log(f"{'─'*60}", color)
    
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
    
    def _fetch_wallet_balance(self):
        """Fetch wallet balance with improved error handling"""
        def _fetch():
            path = "/v2/wallet/balances"
            headers = self._get_headers("GET", path)
            url = f"{self.base_url}{path}"
            
            response = self.delta_session.get(url, headers=headers, timeout=15)
            
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
                            self._log(f"💰 Wallet: ${self.wallet_balance:,.2f}", Fore.GREEN)
                            return True
                    
                    self._log(f"⚠️ No USDT balance found", Fore.YELLOW)
                    return False
                else:
                    error_msg = data.get('error', {}).get('message', 'Unknown error')
                    self._log(f"❌ API error: {error_msg}", Fore.RED)
                    return False
            else:
                self._log(f"❌ HTTP {response.status_code}", Fore.RED)
                return False
                    
        result = self._safe_api_call(_fetch, max_retries=3)
        if not result:
            self._log("⚠️ Using cached wallet values", Fore.YELLOW)
    
    def _initialize_product(self):
        """Initialize trading product"""
        def _fetch_product():
            url = f"{self.base_url}/v2/products"
            response = self.delta_session.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    for product in data.get('result', []):
                        if product.get('symbol') == self.symbol:
                            self.product_id = product.get('id')
                            self.product_symbol = product.get('symbol')
                            self._log(f"✅ Product: {self.product_symbol} (ID: {self.product_id})", Fore.GREEN)
                            return True
            return False
        
        self._log(f"🔍 Initializing {self.symbol}...", Fore.YELLOW)
        result = self._safe_api_call(_fetch_product)
        
        if not result:
            self.product_symbol = self.symbol
            self._log(f"⚠️ Using symbol: {self.symbol}", Fore.YELLOW)
    
    def _get_last_completed_candle_time(self):
        """Get timestamp of last COMPLETED candle"""
        now = datetime.now(self.utc_tz)
        minutes = (now.minute // self.timeframe_minutes) * self.timeframe_minutes
        last_boundary = now.replace(minute=minutes, second=0, microsecond=0)
        last_completed = last_boundary - timedelta(minutes=self.timeframe_minutes)
        return int(last_completed.timestamp())
    
    def _fetch_binance_candles(self, num_candles=100):
        """Fetch completed candles from Binance"""
        def _fetch():
            binance_symbol = self.tv_symbol.replace('BINANCE:', '').replace('USDT', 'USDT')
            url = "https://api.binance.com/api/v3/klines"
            
            params = {
                'symbol': binance_symbol,
                'interval': self.resolution,
                'limit': num_candles + 10
            }
            
            response = self.binance_session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                klines = response.json()
                
                candles = []
                for k in klines:
                    candles.append({
                        'time': int(k[0]) // 1000,
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5])
                    })
                
                # Filter only completed candles
                last_completed_time = self._get_last_completed_candle_time()
                completed = [c for c in candles if c['time'] <= last_completed_time]
                completed.sort(key=lambda x: x['time'])
                
                return completed[-num_candles:] if len(completed) > num_candles else completed
            
            return []
        
        result = self._safe_api_call(_fetch)
        return result if result is not None else []
    
    def _load_historical_candles(self):
        """Load historical candles and initialize indicators"""
        try:
            required_candles = self.rsi_period + self.sma_period + 20
            self._log(f"🔧 Loading {required_candles} completed candles...", Fore.YELLOW)
            
            candles = self._fetch_binance_candles(required_candles)
            
            if len(candles) < self.rsi_period + self.sma_period:
                self._log(f"❌ Insufficient candles: {len(candles)}", Fore.RED)
                return
            
            # Extract close prices
            closes = [float(c['close']) for c in candles]
            timestamps = [c['time'] for c in candles]
            
            # Store price history
            self.price_history = deque(closes, maxlen=self.rsi_period + 100)
            self.candle_timestamps = deque(timestamps, maxlen=self.rsi_period + 100)
            self.last_candle_time = timestamps[-1]
            
            # Initialize RSI calculator with exact TradingView method
            rsi_values = self.rsi_calculator.initialize(closes)
            
            if not rsi_values:
                self._log(f"❌ Failed to initialize RSI", Fore.RED)
                return
            
            # Store RSI history
            self.rsi_history = deque(rsi_values, maxlen=self.sma_period + 10)
            
            # Set current and previous RSI
            self.current_rsi = rsi_values[-1]
            self.prev_rsi = rsi_values[-2] if len(rsi_values) >= 2 else rsi_values[-1]
            
            # Calculate SMA of RSI
            if len(self.rsi_history) >= self.sma_period:
                self.current_sma = SimpleMovingAverage.calculate(self.rsi_history, self.sma_period)
                self.prev_sma = SimpleMovingAverage.calculate(
                    list(self.rsi_history)[:-1], 
                    self.sma_period
                )
            
            # Get RSI state for verification
            rsi_state = self.rsi_calculator.get_current_state()
            
            last_candle_ist = datetime.fromtimestamp(timestamps[-1], self.timezone)
            
            init_details = {
                "Candles Loaded": f"{len(candles)} completed",
                "Timeframe": self.timeframe_display,
                "Last Candle": last_candle_ist.strftime('%Y-%m-%d %H:%M IST'),
                f"RSI({self.rsi_period})": f"{self.current_rsi:.2f}",
                f"SMA({self.sma_period})": f"{self.current_sma:.2f}",
                "Avg Gain": f"{rsi_state['avg_gain']:.6f}",
                "Avg Loss": f"{rsi_state['avg_loss']:.6f}",
                "RS Ratio": f"{rsi_state['rs']:.6f}",
                "State": "RSI > SMA (Bullish)" if self.current_rsi > self.current_sma else "RSI < SMA (Bearish)",
                "Method": "TradingView Exact (Wilder's RMA)"
            }
            self._log_detailed("✅ INITIALIZATION COMPLETE", init_details, Fore.GREEN)
            
        except Exception as e:
            self._log(f"❌ Error loading candles: {e}", Fore.RED)
            import traceback
            self._log(traceback.format_exc(), Fore.RED)
    
    def check_for_new_candle(self):
        """Check if new candle completed"""
        last_completed_time = self._get_last_completed_candle_time()
        
        if last_completed_time != self.last_candle_time:
            candles = self._fetch_binance_candles(1)
            if candles and candles[0]['time'] == last_completed_time:
                return candles[0]
        
        return None
    
    def update_indicators_with_new_candle(self, candle):
        """Update RSI and SMA with new COMPLETED candle"""
        new_close = float(candle['close'])
        prev_close = list(self.price_history)[-1]
        candle_time = candle['time']
        
        # Store previous values
        self.prev_rsi = self.current_rsi
        self.prev_sma = self.current_sma
        
        # Update price history
        self.price_history.append(new_close)
        self.candle_timestamps.append(candle_time)
        self.last_candle_time = candle_time
        
        # Calculate new RSI using TradingView exact method
        self.current_rsi = self.rsi_calculator.update(new_close, prev_close)
        
        # Update RSI history and calculate SMA
        if self.current_rsi is not None:
            self.rsi_history.append(self.current_rsi)
            
            if len(self.rsi_history) >= self.sma_period:
                self.current_sma = SimpleMovingAverage.calculate(self.rsi_history, self.sma_period)
        
        # Log candle details
        candle_time_ist = datetime.fromtimestamp(candle_time, self.timezone)
        
        rsi_state = self.rsi_calculator.get_current_state()
        
        candle_details = {
            "Time": candle_time_ist.strftime('%Y-%m-%d %H:%M IST'),
            "Close": f"${new_close:,.2f}",
            "Change": f"{new_close - prev_close:+.2f}",
            f"RSI({self.rsi_period})": f"{self.prev_rsi:.2f} → {self.current_rsi:.2f}",
            f"SMA({self.sma_period})": f"{self.prev_sma:.2f} → {self.current_sma:.2f}",
            "RSI Change": f"{self.current_rsi - self.prev_rsi:+.2f}",
            "Avg Gain": f"{rsi_state['avg_gain']:.6f}",
            "Avg Loss": f"{rsi_state['avg_loss']:.6f}",
            "Position": "RSI > SMA" if self.current_rsi > self.current_sma else "RSI < SMA"
        }
        self._log_detailed(f"🆕 {self.timeframe_display.upper()} CANDLE COMPLETED", candle_details, Fore.GREEN)
        
        # Detect crossover
        self.detect_crossover()
    
    def detect_crossover(self):
        """Detect RSI-SMA crossover"""
        if self.prev_rsi == 0 or self.prev_sma == 0:
            return
        
        pos = self.get_current_position()
        
        # Bullish crossover: RSI crosses above SMA
        if self.prev_rsi <= self.prev_sma and self.current_rsi > self.current_sma:
            cross_details = {
                "Type": "🟢 BULLISH CROSSOVER",
                "RSI": f"{self.prev_rsi:.2f} → {self.current_rsi:.2f}",
                "SMA": f"{self.prev_sma:.2f} → {self.current_sma:.2f}",
                "Status": "RSI crossed ABOVE SMA",
                "Action": "LONG Entry Signal"
            }
            self._log_detailed("🎯 CROSSOVER DETECTED", cross_details, Fore.GREEN)
            
            # Send Telegram notification FIRST (always notify about crossover)
            if self.telegram.enabled:
                self.telegram.notify_crossover(
                    signal='LONG',
                    prev_rsi=self.prev_rsi,
                    current_rsi=self.current_rsi,
                    prev_sma=self.prev_sma,
                    current_sma=self.current_sma,
                    price=self.current_price or list(self.price_history)[-1]
                )
            
            # THEN check if we should act on it
            if pos['position'] == 'LONG':
                self._log(f"✅ Already LONG - signal ignored", Fore.YELLOW)
                return
            
            # Set pending signal for execution
            self.pending_signal = 'LONG'
        
        # Bearish crossover: RSI crosses below SMA
        elif self.prev_rsi >= self.prev_sma and self.current_rsi < self.current_sma:
            cross_details = {
                "Type": "🔴 BEARISH CROSSOVER",
                "RSI": f"{self.prev_rsi:.2f} → {self.current_rsi:.2f}",
                "SMA": f"{self.prev_sma:.2f} → {self.current_sma:.2f}",
                "Status": "RSI crossed BELOW SMA",
                "Action": "SHORT Entry Signal"
            }
            self._log_detailed("🎯 CROSSOVER DETECTED", cross_details, Fore.RED)
            
            # Send Telegram notification FIRST (always notify about crossover)
            if self.telegram.enabled:
                self.telegram.notify_crossover(
                    signal='SHORT',
                    prev_rsi=self.prev_rsi,
                    current_rsi=self.current_rsi,
                    prev_sma=self.prev_sma,
                    current_sma=self.current_sma,
                    price=self.current_price or list(self.price_history)[-1]
                )
            
            # THEN check if we should act on it
            if pos['position'] == 'SHORT':
                self._log(f"✅ Already SHORT - signal ignored", Fore.YELLOW)
                return
            
            # Set pending signal for execution
            self.pending_signal = 'SHORT'
    
    def get_live_price(self):
        """Get current live price"""
        def _fetch_price():
            binance_symbol = self.tv_symbol.replace('BINANCE:', '').replace('USDT', 'USDT')
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}"
            response = self.binance_session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                price = float(data.get('price', 0))
                self.current_price = price
                return price
            return None
        
        result = self._safe_api_call(_fetch_price)
        return result if result is not None else self.current_price
    
    def get_current_position(self):
        """Get current position"""
        def _fetch_position():
            path = "/v2/positions/margined"
            headers = self._get_headers("GET", path)
            url = f"{self.base_url}{path}"
            
            response = self.delta_session.get(url, headers=headers, timeout=15)
            
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
        
        result = self._safe_api_call(_fetch_position)
        return result if result is not None else {'position': 'FLAT', 'size': 0}
    
    def get_orderbook(self):
        """Get orderbook"""
        def _fetch_orderbook():
            binance_symbol = self.tv_symbol.replace('BINANCE:', '').replace('USDT', 'USDT')
            url = f"https://api.binance.com/api/v3/depth?symbol={binance_symbol}&limit=5"
            response = self.binance_session.get(url, timeout=10)
            
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
        
        result = self._safe_api_call(_fetch_orderbook)
        return result
    
    def place_limit_order(self, side, size, price):
        """Place limit order"""
        def _place_order():
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
            
            response = self.delta_session.post(url, headers=headers, data=body, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    order = data.get('result', {})
                    return {'success': True, 'order': order}
            
            return {'success': False}
        
        result = self._safe_api_call(_place_order)
        return result if result is not None else {'success': False}
    
    def execute_trade(self):
        """Execute pending trade"""
        if not self.pending_signal:
            return
        
        signal = self.pending_signal
        self.pending_signal = None
        
        pos = self.get_current_position()
        orderbook = self.get_orderbook()
        
        if not orderbook:
            self._log(f"❌ No orderbook - retrying signal next cycle", Fore.RED)
            self.pending_signal = signal
            return
        
        # Close existing position
        if pos['position'] != 'FLAT':
            close_side = 'sell' if pos['position'] == 'LONG' else 'buy'
            close_price = orderbook['best_bid'] if close_side == 'sell' else orderbook['best_ask']
            
            self._log(f"🔄 Closing {pos['position']} position...", Fore.YELLOW)
            close_result = self.place_limit_order(close_side, pos['size'], close_price)
            
            if close_result and close_result['success']:
                # Calculate P&L
                pnl = 0
                if self.last_position_entry:
                    if pos['position'] == 'LONG':
                        pnl = (close_price - self.last_position_entry) * pos['size']
                    else:
                        pnl = (self.last_position_entry - close_price) * pos['size']
                    
                    if pnl > 0:
                        self.winning_trades += 1
                    else:
                        self.losing_trades += 1
                    
                    self.total_pnl += pnl
                
                self._log(f"✅ Position closed - P&L: ${pnl:,.2f}", Fore.GREEN if pnl >= 0 else Fore.RED)
                
                # Send Telegram notification for position close
                if self.telegram.enabled:
                    self.telegram.notify_position_closed(
                        direction=pos['position'],
                        size=pos['size'],
                        entry_price=self.last_position_entry or pos['entry_price'],
                        exit_price=close_price,
                        pnl=pnl
                    )
                
                time.sleep(2)
            else:
                self._log(f"❌ Failed to close - will retry", Fore.RED)
                self.pending_signal = signal
                
                # Send error notification
                if self.telegram.enabled:
                    self.telegram.notify_error(f"Failed to close {pos['position']} position")
                return
        
        # Open new position
        entry_side = 'buy' if signal == 'LONG' else 'sell'
        entry_price = orderbook['best_ask'] if entry_side == 'buy' else orderbook['best_bid']
        
        self._log(f"📈 Opening {signal} position...", Fore.CYAN)
        entry_result = self.place_limit_order(entry_side, self.lot_size, entry_price)
        
        if entry_result and entry_result['success']:
            order = entry_result.get('order', {})
            order_id = order.get('id', 'N/A')
            
            # Store entry price for P&L calculation
            self.last_position_entry = entry_price
            self.last_position_size = self.lot_size
            
            entry_details = {
                "Action": f"{signal} OPENED",
                "Price": f"${entry_price:,.2f}",
                "Size": f"{self.lot_size} contracts",
                "Order ID": order_id,
                "RSI": f"{self.current_rsi:.2f}",
                "SMA": f"{self.current_sma:.2f}",
                "Spread": f"${orderbook['spread']:.2f}",
                "Method": "TradingView Exact"
            }
            self._log_detailed("✅ TRADE EXECUTED", entry_details, Fore.GREEN)
            self.trade_count += 1
            
            # Send Telegram notification for position open
            if self.telegram.enabled:
                self.telegram.notify_position_opened(
                    direction=signal,
                    size=self.lot_size,
                    price=entry_price,
                    rsi=self.current_rsi,
                    sma=self.current_sma,
                    orderbook=orderbook
                )
        else:
            self._log(f"❌ Failed to open {signal}", Fore.RED)
            
            # Send error notification
            if self.telegram.enabled:
                self.telegram.notify_error(f"Failed to open {signal} position")
    
    def print_status(self):
        """Print current status"""
        self._check_connection_health()
        
        pos = self.get_current_position()
        price = self.get_live_price()
        
        if self.last_candle_time:
            last_candle_ist = datetime.fromtimestamp(self.last_candle_time, self.timezone)
            last_candle_str = last_candle_ist.strftime('%H:%M:%S IST')
        else:
            last_candle_str = "N/A"
        
        time_since_success = time.time() - self.last_successful_api_call
        
        if time_since_success < 60:
            connection_status = "🟢 HEALTHY"
        elif time_since_success < 180:
            connection_status = "🟡 SLOW"
        else:
            connection_status = "🔴 ISSUES"
        
        # Get RSI internal state
        rsi_state = self.rsi_calculator.get_current_state()
        
        # Calculate win rate
        total_closed = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_closed * 100) if total_closed > 0 else 0
        
        status_details = {
            "Connection": f"{connection_status} ({time_since_success:.0f}s ago)",
            "Binance Data": "🟢 ACTIVE" if price else "🔴 FAILED",
            "Live Price": f"${price:,.2f}" if price else "N/A",
            "Last Candle": last_candle_str,
            f"RSI({self.rsi_period})": f"{self.current_rsi:.2f}",
            f"SMA({self.sma_period})": f"{self.current_sma:.2f}",
            "RSI vs SMA": "ABOVE (Bullish)" if self.current_rsi > self.current_sma else "BELOW (Bearish)",
            "Avg Gain": f"{rsi_state['avg_gain']:.6f}",
            "Avg Loss": f"{rsi_state['avg_loss']:.6f}",
            "Position": pos['position'],
            "Size": f"{pos['size']} contracts" if pos['position'] != 'FLAT' else "N/A",
            "Unrealized P&L": f"${pos.get('pnl', 0):,.2f}" if pos['position'] != 'FLAT' else "N/A",
            "Total Trades": self.trade_count,
            "Closed Trades": total_closed,
            "Wins/Losses": f"{self.winning_trades}/{self.losing_trades}",
            "Win Rate": f"{win_rate:.1f}%",
            "Total P&L": f"${self.total_pnl:,.2f}",
            "Wallet": f"${self.wallet_balance:,.2f}" if self.wallet_balance > 0 else "Not fetched",
            "Telegram": "🟢 ENABLED" if self.telegram.enabled else "🔴 DISABLED",
            "Method": "TradingView Exact (Wilder's RMA)"
        }
        
        self._log_detailed("📊 BOT STATUS", status_details, Fore.CYAN)
    
    def run(self):
        """Main bot loop"""
        startup_details = {
            "Symbol": self.symbol,
            "Strategy": "RSI-SMA Crossover",
            "RSI Period": self.rsi_period,
            "SMA Period": self.sma_period,
            "Timeframe": self.timeframe_display,
            "Lot Size": f"{self.lot_size} contracts",
            "Current RSI": f"{self.current_rsi:.2f}",
            "Current SMA": f"{self.current_sma:.2f}",
            "Execution": "Immediate on crossover",
            "Method": "TradingView Exact (Wilder's RMA)",
            "Telegram": "ENABLED" if self.telegram.enabled else "DISABLED",
            "Status": "ACTIVE"
        }
        self._log_detailed("🚀 BOT STARTED", startup_details, Fore.GREEN)
        
        loop_count = 0
        status_interval = 20
        health_check_interval = 60
        
        try:
            while True:
                loop_count += 1
                
                # Health check
                if loop_count % health_check_interval == 0:
                    self._check_connection_health()
                
                # Check for new candle
                try:
                    new_candle = self.check_for_new_candle()
                    if new_candle:
                        self.update_indicators_with_new_candle(new_candle)
                except Exception as e:
                    self._log(f"⚠️ Error checking candle: {str(e)[:100]}", Fore.YELLOW)
                    self.api_failure_count += 1
                
                # Execute pending trades
                if self.pending_signal:
                    try:
                        self.execute_trade()
                    except Exception as e:
                        self._log(f"⚠️ Error executing trade: {str(e)[:100]}", Fore.YELLOW)
                        if self.telegram.enabled:
                            self.telegram.notify_error(f"Trade execution error: {str(e)[:100]}")
                
                # Print status periodically
                if loop_count % status_interval == 0:
                    try:
                        self.print_status()
                    except Exception as e:
                        self._log(f"⚠️ Error printing status: {str(e)[:100]}", Fore.YELLOW)
                
                # Update price periodically
                if loop_count % 3 == 0:
                    try:
                        self.get_live_price()
                    except Exception as e:
                        if loop_count % 50 == 0:
                            self._log(f"⚠️ Error fetching price: {str(e)[:100]}", Fore.YELLOW)
                
                # Send periodic summary every 100 loops (approx 8 minutes)
                if loop_count % 100 == 0 and self.telegram.enabled:
                    total_closed = self.winning_trades + self.losing_trades
                    if total_closed > 0:
                        self.telegram.notify_trade_summary(
                            total_trades=self.trade_count,
                            win_count=self.winning_trades,
                            loss_count=self.losing_trades,
                            total_pnl=self.total_pnl
                        )
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            self._log("\n🛑 Shutdown signal received...", Fore.YELLOW)
            
            try:
                pos = self.get_current_position()
                total_closed = self.winning_trades + self.losing_trades
                win_rate = (self.winning_trades / total_closed * 100) if total_closed > 0 else 0
                
                shutdown_details = {
                    "Total Trades": self.trade_count,
                    "Closed Trades": total_closed,
                    "Wins": self.winning_trades,
                    "Losses": self.losing_trades,
                    "Win Rate": f"{win_rate:.1f}%",
                    "Total P&L": f"${self.total_pnl:,.2f}",
                    "Final RSI": f"{self.current_rsi:.2f}",
                    "Final SMA": f"{self.current_sma:.2f}",
                    "Position": pos['position'],
                    "Status": "STOPPED BY USER"
                }
                self._log_detailed("🛑 BOT STOPPED", shutdown_details, Fore.YELLOW)
                
                # Send shutdown notification
                if self.telegram.enabled:
                    self.telegram.notify_bot_shutdown(
                        total_trades=self.trade_count,
                        wins=self.winning_trades,
                        losses=self.losing_trades,
                        total_pnl=self.total_pnl
                    )
            except:
                self._log("🛑 Bot stopped", Fore.YELLOW)
            
            try:
                self.delta_session.close()
                self.binance_session.close()
                self._log("✅ Sessions closed cleanly", Fore.GREEN)
            except:
                pass
        
        except Exception as e:
            self._log(f"❌ Critical error: {str(e)[:200]}", Fore.RED)
            import traceback
            self._log(traceback.format_exc(), Fore.RED)
            self._log("🔄 Bot attempting to recover...", Fore.YELLOW)
            
            # Send error notification
            if self.telegram.enabled:
                self.telegram.notify_error(f"Critical error: {str(e)[:150]}")
            
            self._reset_sessions()
            time.sleep(10)
            self._log("🔄 Attempting to restart...", Fore.YELLOW)
            
            try:
                self.run()
            except:
                self._log("❌ Unable to restart. Manual intervention needed.", Fore.RED)


if __name__ == "__main__":
    bot = AccurateRSISMABot()
    bot.run()
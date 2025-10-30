"""
Configuration management for Delta Exchange Trading Bot
"""
import os
import requests
import time
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration loaded from environment variables"""

    # Delta Exchange API
    DELTA_API_KEY = os.getenv('DELTA_API_KEY')
    DELTA_API_SECRET = os.getenv('DELTA_API_SECRET')
    DELTA_REGION = os.getenv('DELTA_REGION', 'india').lower()
    USE_TESTNET = os.getenv('USE_TESTNET', 'False').lower() == 'true'
    TAAPI_SECRET_KEY = os.getenv('TAAPI_SECRET_KEY')

    # Trading Parameters
    TV_SYMBOL = os.getenv('TV_SYMBOL', 'BINANCE:BTCUSDT')
    USE_TRADINGVIEW_FALLBACK = os.getenv('USE_TRADINGVIEW_FALLBACK', 'True').lower() == 'true'
    SYMBOL = os.getenv('SYMBOL', 'BTCUSDT')
    LOT_SIZE = float(os.getenv('LOT_SIZE', '0.001'))
    ORDER_SIZE = float(os.getenv('ORDER_SIZE', '0.01'))
    SMA_PERIOD = int(os.getenv('SMA_PERIOD', '21'))
    RSI_OVERBOUGHT = int(os.getenv('RSI_OVERBOUGHT', '70'))
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
    RSI_OVERSOLD = int(os.getenv('RSI_OVERSOLD', '30'))
    TIMEFRAME_1M = int(os.getenv('TIMEFRAME_1M', '60'))

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    # API
    API_PORT = int(os.getenv('API_PORT', '8080'))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'trading_bot.log')

    # API URLs - CORRECTED based on your working URLs
    @classmethod
    def get_base_url(cls):
        """Get the correct API base URL based on region and testnet setting"""
        if cls.USE_TESTNET:
            return 'https://cdn-ind.testnet.deltaex.org'
        else:
            if cls.DELTA_REGION == 'india':
                return 'https://api.india.delta.exchange'
            else:
                return 'https://api.delta.exchange'

    @classmethod
    def _set_api_url(cls):
        """Initialize the API URL based on current settings"""
        cls.DELTA_API_URL = cls.get_base_url()

    @staticmethod
    def generate_signature(api_secret, message):
        """Generate HMAC-SHA256 signature for API requests"""
        return hmac.new(
            api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @classmethod
    def get_auth_headers(cls, method, path, body=''):
        """Generate authenticated headers for Delta Exchange API"""
        timestamp = str(int(time.time()))
        message = method + timestamp + path + body
        signature = cls.generate_signature(cls.DELTA_API_SECRET, message)

        return {
            'api-key': cls.DELTA_API_KEY,
            'timestamp': timestamp,
            'signature': signature,
            'Content-Type': 'application/json',
            'User-Agent': 'python-trading-bot'
        }

    @classmethod
    def test_connection(cls):
        """Test API connection and return status"""
        base_url = cls.get_base_url()

        # Test public endpoint
        try:
            response = requests.get(f"{base_url}/v2/products", timeout=10)
            if response.status_code != 200:
                return False, f"Public endpoint unreachable: HTTP {response.status_code}"
                
            # Check if response contains expected data
            data = response.json()
            if not data.get('success', False):
                return False, "API returned success=false on public endpoint"
                
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection error: {e}"
        except requests.exceptions.Timeout as e:
            return False, f"Timeout error: {e}"
        except Exception as e:
            return False, f"Public endpoint error: {e}"

        # Test authentication only if API keys are provided
        if not cls.DELTA_API_KEY or not cls.DELTA_API_SECRET:
            return True, "Public endpoint accessible (no auth test - missing API keys)"

        # Test authentication
        try:
            path = "/v2/wallet/balances"
            headers = cls.get_auth_headers("GET", path)
            response = requests.get(f"{base_url}{path}", headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return True, "Connection and authentication successful"
                else:
                    return False, "API returned success=false on authenticated endpoint"
            else:
                data = response.json()
                error_msg = data.get('error', {}).get('message', 'Unknown error')
                return False, f"Authentication failed: {error_msg}"
        except Exception as e:
            return False, f"Auth test error: {e}"

    @classmethod
    def get_wallet_balance(cls, verbose=False):
        """
        Fetch wallet balances from Delta Exchange

        Args:
            verbose: If True, prints detailed balance info

        Returns:
            dict: Balance data or None if error
        """
        base_url = cls.get_base_url()
        path = "/v2/wallet/balances"

        # Check if API keys are available
        if not cls.DELTA_API_KEY or not cls.DELTA_API_SECRET:
            if verbose:
                print("❌ API keys not configured - cannot fetch wallet balance")
            return {'success': False, 'error': 'API keys not configured'}

        try:
            headers = cls.get_auth_headers("GET", path)
            response = requests.get(f"{base_url}{path}", headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    balances = data.get('result', [])

                    if verbose:
                        print("\n" + "=" * 70)
                        print("  💰 DELTA EXCHANGE WALLET")
                        print("=" * 70)

                        if not balances:
                            print("\n  No assets in wallet.")
                        else:
                            total_balance = 0
                            for asset in balances:
                                asset_id = asset.get('asset_id', 'Unknown')
                                balance = float(asset.get('balance', 0))
                                available = float(asset.get('available_balance', 0))
                                
                                if balance > 0 or available > 0:
                                    total_balance += balance
                                    print(f"\n  Asset: {asset_id}")
                                    print(f"  ├─ Total: {balance:,.8f}")
                                    print(f"  ├─ Available: {available:,.8f}")
                                    print(f"  └─ Locked: {(balance - available):,.8f}")
                            
                            if total_balance > 0:
                                print(f"\n  💵 Total Balance: {total_balance:,.8f}")

                        print("\n" + "=" * 70)
                        print(f"\n✅ Found {len(balances)} asset(s)\n")

                    return {
                        'success': True,
                        'balances': balances,
                        'count': len(balances)
                    }
                else:
                    return {'success': False, 'error': 'API returned success=false'}
            else:
                return {
                    'success': False,
                    'error': f"Status {response.status_code}: {response.text[:200]}"
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @classmethod
    def get_positions(cls, verbose=False):
        """
        Fetch current open positions

        Args:
            verbose: If True, prints position details

        Returns:
            dict: Position data or None if error
        """
        base_url = cls.get_base_url()
        path = "/v2/positions/margined"

        # Check if API keys are available
        if not cls.DELTA_API_KEY or not cls.DELTA_API_SECRET:
            if verbose:
                print("❌ API keys not configured - cannot fetch positions")
            return {'success': False, 'error': 'API keys not configured'}

        try:
            headers = cls.get_auth_headers("GET", path)
            response = requests.get(f"{base_url}{path}", headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    positions = data.get('result', [])

                    if verbose:
                        print("\n" + "=" * 70)
                        print("  📊 OPEN POSITIONS")
                        print("=" * 70)

                        if not positions:
                            print("\n  No open positions.")
                        else:
                            for pos in positions:
                                symbol = pos.get('product_symbol', 'Unknown')
                                size = float(pos.get('size', 0))
                                entry = float(pos.get('entry_price', 0))
                                pnl = float(pos.get('unrealized_pnl', 0))
                                
                                position_type = "LONG" if size > 0 else "SHORT" if size < 0 else "FLAT"
                                pnl_color = "🟢" if pnl >= 0 else "🔴"

                                print(f"\n  {symbol} ({position_type})")
                                print(f"  ├─ Size: {abs(size):.4f}")
                                print(f"  ├─ Entry: ${entry:,.2f}")
                                print(f"  └─ Unrealized P&L: {pnl_color} ${pnl:,.2f}")

                        print("\n" + "=" * 70)
                        print(f"\n✅ Found {len(positions)} position(s)\n")

                    return {
                        'success': True,
                        'positions': positions,
                        'count': len(positions)
                    }
                else:
                    return {'success': False, 'error': 'API returned success=false'}
            else:
                return {
                    'success': False,
                    'error': f"Status {response.status_code}: {response.text[:200]}"
                }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []

        if not cls.DELTA_API_KEY:
            errors.append("DELTA_API_KEY is required")
        if not cls.DELTA_API_SECRET:
            errors.append("DELTA_API_SECRET is required")
        if not cls.SYMBOL:
            errors.append("SYMBOL is required")
        if cls.LOT_SIZE <= 0:
            errors.append("LOT_SIZE must be positive")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        # Test connection
        print("\n🔄 Testing Delta Exchange connection...")
        success, message = cls.test_connection()

        if success:
            print(f"✅ {message}")
            print(f"📍 Using: {cls.get_base_url()}")
            print(f"🧪 Testnet: {cls.USE_TESTNET}")
            print(f"📈 Symbol: {cls.SYMBOL}")
            print(f"📊 Lot Size: {cls.LOT_SIZE}")

            # Show wallet balance on startup if API keys are available
            if cls.DELTA_API_KEY and cls.DELTA_API_SECRET:
                cls.get_wallet_balance(verbose=True)
                cls.get_positions(verbose=True)

        else:
            print(f"❌ Error: {message}")
            print(f"🔧 Check your API keys and network connection")
            print(f"🌐 API URL: {cls.get_base_url()}")

        return success


# Initialize API URL
Config._set_api_url()

# Validate configuration on import
if __name__ != "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(f"⚠️  Configuration warning: {e}")

# If run directly, show detailed diagnostics
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  DELTA EXCHANGE CONFIG DIAGNOSTICS")
    print("=" * 70)

    print(f"\n📍 Region: {Config.DELTA_REGION}")
    print(f"🔗 API URL: {Config.get_base_url()}")
    print(f"🧪 Testnet: {Config.USE_TESTNET}")
    print(f"📈 Symbol: {Config.SYMBOL}")
    print(f"📊 Lot Size: {Config.LOT_SIZE}")

    # Test connection
    success, message = Config.test_connection()
    print(f"\n{'✅' if success else '❌'} Connection: {message}")

    if success and Config.DELTA_API_KEY and Config.DELTA_API_SECRET:
        # Show wallet balance
        Config.get_wallet_balance(verbose=True)

        # Show positions
        Config.get_positions(verbose=True)
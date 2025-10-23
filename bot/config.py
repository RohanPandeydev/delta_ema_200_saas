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
    TESTNET = os.getenv('TESTNET', 'False').lower() == 'true'

    # Trading Parameters
    SYMBOL = os.getenv('SYMBOL', 'ETHUSD')
  
    LOT_SIZE = float(os.getenv('LOT_SIZE', '1'))
   
    TIMEFRAME_1M = int(os.getenv('TIMEFRAME_1M', '1'))
    

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    # API
    API_PORT = int(os.getenv('API_PORT', '8080'))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'trading_bot.log')

    # API URLs - FIXED for India region
    @classmethod
    def get_base_url(cls):
        """Get the correct API base URL based on region and testnet setting"""
        if cls.TESTNET:
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
    def get_auth_headers(cls, method, path):
        """Generate authenticated headers for Delta Exchange API"""
        timestamp = str(int(time.time()))
        message = method + timestamp + path
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
                return False, "Public endpoint unreachable"
        except Exception as e:
            return False, f"Connection error: {e}"

        # Test authentication
        try:
            path = "/v2/wallet/balances"
            headers = cls.get_auth_headers("GET", path)
            response = requests.get(f"{base_url}{path}", headers=headers, timeout=10)

            if response.status_code == 200:
                return True, "Connection successful"
            else:
                data = response.json()
                error_msg = data.get('error', {}).get('code', 'Unknown error')
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
                            for asset in balances:
                                asset_id = asset.get('asset_id', 'Unknown')
                                balance = float(asset.get('balance', 0))
                                available = float(asset.get('available_balance', 0))

                                if balance > 0 or available > 0:
                                    print(f"\n  Asset: {asset_id}")
                                    print(f"  ├─ Total: {balance:,.8f}")
                                    print(f"  ├─ Available: {available:,.8f}")
                                    print(f"  └─ Locked: {(balance - available):,.8f}")

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
                                size = pos.get('size', 0)
                                entry = pos.get('entry_price', 0)
                                pnl = pos.get('unrealized_pnl', 0)

                                print(f"\n  {symbol}")
                                print(f"  ├─ Size: {size}")
                                print(f"  ├─ Entry: {entry}")
                                print(f"  └─ Unrealized P&L: {pnl}")

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
        # if cls.ORDER_SIZE <= 0:
        #     errors.append("ORDER_SIZE must be positive")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        # Test connection
        print("\n🔄 Testing Delta Exchange connection...")
        success, message = cls.test_connection()

        if success:
            print(f"✅ {message}")
            print(f"📍 Using: {cls.get_base_url()}")

            # Show wallet balance on startup
            cls.get_wallet_balance(verbose=True)

        else:
            print(f"⚠️  Warning: {message}")
            print(f"🔧 Check your API keys and region setting (DELTA_REGION={cls.DELTA_REGION})")

        return True


# Initialize API URL
Config._set_api_url()

# Validate configuration on import
if __name__ != "__main__":
    Config.validate()

# If run directly, show detailed diagnostics
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  DELTA EXCHANGE CONFIG DIAGNOSTICS")
    print("=" * 70)

    print(f"\n📍 Region: {Config.DELTA_REGION}")
    print(f"🔗 API URL: {Config.get_base_url()}")
    print(f"🧪 Testnet: {Config.TESTNET}")

    # Test connection
    success, message = Config.test_connection()
    print(f"\n{'✅' if success else '❌'} Connection: {message}")

    if success:
        # Show wallet balance
        Config.get_wallet_balance(verbose=True)

        # Show positions
        Config.get_positions(verbose=True)
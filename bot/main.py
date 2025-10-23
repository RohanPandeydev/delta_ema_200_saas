import os
import time
import sys
from datetime import datetime

def log(message, level="INFO"):
    """Print formatted log message"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}", flush=True)

def main():
    """Main bot loop"""
    # Get configuration from environment
    user_id = os.getenv('USER_ID', 'unknown')
    cred_id = os.getenv('CREDENTIAL_ID', 'unknown')
    api_key = os.getenv('DELTA_API_KEY', '')
    symbol = os.getenv('SYMBOL', 'BTCUSD')
    lot_size = os.getenv('LOT_SIZE', '60')
    timeframe = os.getenv('TIMEFRAME_1M', '15')
    
    log("=" * 80)
    log("🚀 TRADING BOT STARTING", "INFO")
    log("=" * 80)
    log(f"User ID: {user_id}")
    log(f"Credential ID: {cred_id}")
    log(f"Symbol: {symbol}")
    log(f"Lot Size: {lot_size}")
    log(f"Timeframe: {timeframe}m")
    log(f"API Key: {api_key[:10]}..." if api_key else "API Key: Not set")
    log("=" * 80)
    
    if not api_key:
        log("⚠️  WARNING: No API key provided!", "ERROR")
    
    # Simulate trading activity
    trade_count = 0
    
    try:
        while True:
            log(f"💹 Monitoring {symbol} market...")
            time.sleep(10)
            
            # Simulate market data
            import random
            price = 45000 + random.uniform(-1000, 1000)
            ema = 45000 + random.uniform(-500, 500)
            
            log(f"📊 Price: ${price:,.2f} | EMA-200: ${ema:,.2f}")
            
            # Simulate trading decision
            if random.random() > 0.9:  # 10% chance of trade
                trade_count += 1
                side = "LONG" if price > ema else "SHORT"
                log(f"🎯 Signal detected: {side}", "SUCCESS")
                log(f"📤 Placing order: {side} {lot_size} @ ${price:,.2f}")
                time.sleep(2)
                log(f"✅ Trade #{trade_count} executed successfully!", "SUCCESS")
            
            time.sleep(20)  # Wait before next check
            
    except KeyboardInterrupt:
        log("🛑 Bot stopped by user", "INFO")
    except Exception as e:
        log(f"❌ Error: {str(e)}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
import time
import random
from datetime import datetime

class MockDockerManager:
    """
    Mock Docker manager for Windows development
    Simulates Docker operations without requiring Docker Desktop
    """
    
    def __init__(self):
        print("🔧 Using Mock Docker Manager (Windows Development Mode)")
        self.containers = {}
        self.use_mock = True
        self._container_counter = 0
    
    def create_bot_container(self, user, bot_config):
        """Mock container creation with proper tracking"""
        container_name = f"{user.username}_{user.id}_{bot_config.bot_name}"
        self._container_counter += 1
        container_id = f"mock_{int(time.time())}_{self._container_counter}"
        
        print(f"🚀 [MOCK] Creating container: {container_name}")
        print(f"📝 [MOCK] Container ID: {container_id}")
        print(f"📝 [MOCK] Bot type: {bot_config.bot_type}")
        print(f"📝 [MOCK] Symbol: {bot_config.symbol}")
        print(f"📝 [MOCK] Timeframe: {bot_config.timeframe}")
        
        if bot_config.bot_type == 'EMA':
            print(f"📝 [MOCK] EMA Period: {bot_config.ema_period}")
        elif bot_config.bot_type == 'RSI_SMA':
            print(f"📝 [MOCK] RSI Period: {bot_config.rsi_period}")
            print(f"📝 [MOCK] SMA Period: {bot_config.sma_period}")
        
        # Create initial logs
        initial_logs = self._generate_initial_logs(bot_config)
        
        # Store mock container info
        self.containers[container_id] = {
            'id': container_id,
            'name': container_name,
            'status': 'running',
            'bot_type': bot_config.bot_type,
            'symbol': bot_config.symbol,
            'created_at': datetime.now(),
            'logs': initial_logs,
            'user_id': user.id,
            'bot_name': bot_config.bot_name
        }
        
        print(f"✅ [MOCK] Container stored: {container_id}")
        print(f"📊 [MOCK] Total containers: {len(self.containers)}")
        
        return container_id, container_name
    
    def _generate_initial_logs(self, bot_config):
        """Generate initial startup logs"""
        logs = []
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logs.append(f"[{current_time}] 🚀 Starting {bot_config.bot_type} Trading Bot")
        logs.append(f"[{current_time}] 📊 Symbol: {bot_config.symbol}")
        logs.append(f"[{current_time}] ⏰ Timeframe: {bot_config.timeframe}m")
        
        if bot_config.bot_type == 'EMA':
            logs.append(f"[{current_time}] 📈 EMA Period: {bot_config.ema_period}")
            logs.append(f"[{current_time}] 🔄 EMA Crossover Strategy Active")
        elif bot_config.bot_type == 'RSI_SMA':
            logs.append(f"[{current_time}] 📊 RSI Period: {bot_config.rsi_period}")
            logs.append(f"[{current_time}] 📈 SMA Period: {bot_config.sma_period}")
            logs.append(f"[{current_time}] 🔄 RSI-SMA Crossover Strategy Active")
        
        logs.append(f"[{current_time}] ✅ Bot initialized successfully")
        logs.append(f"[{current_time}] 📈 Connecting to Delta Exchange...")
        logs.append(f"[{current_time}] 🔄 Starting market data feed...")
        logs.append(f"[{current_time}] 🎯 Trading bot is now LIVE")
        
        return logs
    
    def _generate_live_log(self, bot_type, symbol):
        """Generate realistic live trading logs"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        price = random.randint(30000, 50000)
        volume = random.randint(1000, 50000)
        
        log_templates = [
            f"[{current_time}] 📊 {symbol} - Price: ${price:,} | Volume: {volume}",
            f"[{current_time}] 🔍 Analyzing market conditions...",
            f"[{current_time}] 📈 Checking technical indicators...",
            f"[{current_time}] 💹 Market volatility: {random.randint(1, 10)}/10",
            f"[{current_time}] 📉 Spread: {random.uniform(0.1, 2.0):.2f}%",
            f"[{current_time}] 🔄 Live data feed active",
            f"[{current_time}] ✅ All systems operational",
            f"[{current_time}] 🎯 No trading signals detected",
            f"[{current_time}] 💰 Account balance: ${random.randint(1000, 50000):,}",
        ]
        
        # Add bot-specific logs
        if bot_type == 'EMA':
            ema_logs = [
                f"[{current_time}] 📈 EMA Fast: ${random.randint(29000, 49000):,}",
                f"[{current_time}] 📈 EMA Slow: ${random.randint(29500, 49500):,}",
                f"[{current_time}] 🔄 EMA Cross analysis running",
            ]
            log_templates.extend(ema_logs)
        elif bot_type == 'RSI_SMA':
            rsi_logs = [
                f"[{current_time}] 📊 RSI: {random.randint(30, 70)}",
                f"[{current_time}] 📈 SMA: {random.randint(20, 50)}",
                f"[{current_time}] 🔄 RSI-SMA crossover monitoring...",
            ]
            log_templates.extend(rsi_logs)
        
        return random.choice(log_templates)
    
    def stop_bot(self, container_id):
        """Mock stop container"""
        if container_id in self.containers:
            self.containers[container_id]['status'] = 'stopped'
            
            # Add stop log
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.containers[container_id]['logs'].append(f"[{current_time}] ⏸️ Bot stopped by user")
            
            print(f"⏸️ [MOCK] Stopped container: {container_id}")
            return True
        
        print(f"❌ [MOCK] Container not found for stop: {container_id}")
        print(f"📊 [MOCK] Available containers: {list(self.containers.keys())}")
        return False
    
    def delete_bot(self, container_id):
        """Mock delete container"""
        if container_id in self.containers:
            container_name = self.containers[container_id]['name']
            del self.containers[container_id]
            print(f"🗑️ [MOCK] Deleted container: {container_id} ({container_name})")
            print(f"📊 [MOCK] Remaining containers: {len(self.containers)}")
            return True
        
        print(f"❌ [MOCK] Container not found for delete: {container_id}")
        print(f"📊 [MOCK] Available containers: {list(self.containers.keys())}")
        return False
    
    def get_logs(self, container_id, tail=100):
        """Mock container logs with proper container tracking"""
        print(f"📋 [MOCK] Fetching logs for: {container_id}")
        print(f"📊 [MOCK] Available containers: {list(self.containers.keys())}")
        
        if container_id in self.containers:
            container = self.containers[container_id]
            
            # Add a new live log entry
            new_log = self._generate_live_log(container['bot_type'], container['symbol'])
            container['logs'].append(new_log)
            
            # Keep only recent logs
            if len(container['logs']) > tail:
                container['logs'] = container['logs'][-tail:]
            
            logs_text = "\n".join(container['logs'])
            print(f"✅ [MOCK] Logs fetched successfully for: {container_id}")
            return logs_text
        
        error_msg = f"❌ Container {container_id} not found. Available containers: {list(self.containers.keys())}"
        print(error_msg)
        return error_msg
    
    def stream_logs(self, container_id):
        """Mock log streaming"""
        if container_id in self.containers:
            counter = 0
            while True:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                container = self.containers[container_id]
                
                if counter % 5 == 0:
                    log_line = f"[{current_time}] 📊 Market data update - {container['symbol']}: ${random.randint(30000, 50000):,}"
                else:
                    log_line = f"[{current_time}] 🔍 Analyzing {container['symbol']} price action..."
                
                yield log_line
                time.sleep(3)  # Simulate real-time logs
                counter += 1
        else:
            yield f"❌ Container {container_id} not found"
    
    def list_containers(self):
        """List all mock containers (for debugging)"""
        return self.containers
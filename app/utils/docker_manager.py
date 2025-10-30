import time
import random
import docker
import os
import platform
from datetime import datetime
from docker.errors import DockerException


# -------------------------------------------------------------------
# Base Docker Manager
# -------------------------------------------------------------------
class DockerManagerBase:
    """Base class for Docker management"""

    def __init__(self):
        self.containers = {}

    def create_bot_container(self, user, bot_config):
        raise NotImplementedError()

    def list_containers(self):
        raise NotImplementedError()

    def get_container(self, container_id):
        raise NotImplementedError()

    def stream_logs(self, container_id):
        raise NotImplementedError()

    def stop_bot(self, container_id):
        raise NotImplementedError()

    def stop_container(self, container_id):
        raise NotImplementedError()

    def delete_bot(self, container_id):
        raise NotImplementedError()

    def get_logs(self, container_id):
        raise NotImplementedError()

    def start_bot(self, container_id):
        raise NotImplementedError()

    def get_container_status(self, container_id):
        raise NotImplementedError()


# -------------------------------------------------------------------
# Real Docker Manager
# -------------------------------------------------------------------
class RealDockerManager(DockerManagerBase):
    """Handles real Docker containers"""

    def __init__(self):
        super().__init__()
        try:
            # Try Windows named pipe first
            self.client = docker.DockerClient(base_url='npipe:////./pipe/docker_engine')
        except:
            try:
                # Try default Docker environment
                self.client = docker.from_env()
            except:
                # Try TCP connection as last resort
                self.client = docker.DockerClient(base_url='tcp://localhost:2375')
        print("🐳 Using Real Docker Manager")

    def create_bot_container(self, user, bot_config):
        """Create a real Docker container for a bot"""
        try:
            # Replace spaces with hyphens and remove any other invalid characters
            sanitized_bot_name = bot_config.bot_name.replace(' ', '-')
            container_name = f"{user.username}_{user.id}_{sanitized_bot_name}"

            # Prepare environment variables
            environment = {
                # Basic Bot Configuration
                "BOT_TYPE": bot_config.bot_type,
                "BOT_NAME": bot_config.bot_name,
                
                # Delta Exchange Credentials
                "DELTA_API_KEY": bot_config.delta_api_key,
                "DELTA_API_SECRET": bot_config.delta_api_secret,
                "DELTA_REGION": getattr(bot_config, 'delta_region', 'india'),
                
                # Trading Configuration
                "SYMBOL": bot_config.symbol,
                "LOT_SIZE": str(bot_config.lot_size),
                "TIMEFRAME": str(bot_config.timeframe),
                "TIMEFRAME_TYPE": getattr(bot_config, 'timeframe_type', 'm'),
                
                # Exchange Settings
                "TESTNET": str(getattr(bot_config, 'testnet', False)).lower(),
                
                # HTTP API Configuration
                "API_PORT": str(getattr(bot_config, 'api_port', 8080)),
                
                # Logging Configuration
                "LOG_LEVEL": getattr(bot_config, 'log_level', 'INFO'),
                "LOG_FILE": getattr(bot_config, 'log_file', 'trading_bot.log'),
                
                # Container Identification
                "CONTAINER_ID": container_name,
            }

            # Bot type specific configs
            if bot_config.bot_type == "EMA":
                environment.update({
                    "EMA_PERIOD": str(bot_config.ema_period),
                })
            elif bot_config.bot_type == "RSI_SMA":
                environment.update({
                    "RSI_PERIOD": str(bot_config.rsi_period),
                    "RSI_OVERBOUGHT": str(bot_config.rsi_overbought),
                    "RSI_OVERSOLD": str(bot_config.rsi_oversold),
                    "SMA_PERIOD": str(bot_config.sma_period),
                    "TV_SYMBOL": getattr(bot_config, 'tv_symbol', 'BTCUSDT'),
                    "USE_TRADINGVIEW_FALLBACK": str(getattr(bot_config, 'use_tradingview_fallback', True)).lower(),
                })

            # Telegram setup
            if getattr(bot_config, 'telegram_bot_token', None) and getattr(bot_config, 'telegram_chat_id', None):
                environment.update({
                    "TELEGRAM_BOT_TOKEN": bot_config.telegram_bot_token,
                    "TELEGRAM_CHAT_ID": bot_config.telegram_chat_id
                })

            # TAAPI Configuration
            if getattr(bot_config, 'taapi_secret_key', None):
                environment.update({
                    "TAAPI_SECRET_KEY": bot_config.taapi_secret_key
                })

            # Determine network mode (host networking is not supported on Windows)
            network_mode = "host" if platform.system().lower() != 'windows' else None

            run_kwargs = {
                'image': "trading-bot:latest",
                'name': container_name,
                'environment': environment,
                'detach': True,
                'restart_policy': {"Name": "unless-stopped"},
            }

            if network_mode:
                run_kwargs['network_mode'] = network_mode

            # Create container
            container = self.client.containers.run(**run_kwargs)

            print(f"✅ Created container: {container.id} ({container_name})")
            return container.id, container_name

        except Exception as e:
            print(f"❌ Container creation error: {str(e)}")
            raise

    def list_containers(self):
        return [c.id for c in self.client.containers.list(filters={"ancestor": "trading-bot:latest"})]

    def get_container(self, container_id):
        try:
            return self.client.containers.get(container_id)
        except:
            return None

    def stream_logs(self, container_id):
        try:
            container = self.get_container(container_id)
            if container:
                # First yield existing logs
                for log in container.logs(tail=50).decode('utf-8').splitlines():
                    yield log
                # Then stream new logs
                for log in container.logs(stream=True, follow=True):
                    yield log.decode('utf-8').strip()
        except Exception as e:
            yield f"❌ Error streaming logs: {str(e)}"

    def stop_bot(self, container_id):
        return self.stop_container(container_id)

    def stop_container(self, container_id):
        try:
            container = self.get_container(container_id)
            if container:
                container.stop()
                print(f"🛑 Container stopped: {container_id}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error stopping container: {str(e)}")
            return False

    def start_bot(self, container_id):
        """Start a stopped container"""
        try:
            container = self.get_container(container_id)
            if container:
                container.start()
                print(f"▶️ Container started: {container_id}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error starting container: {str(e)}")
            return False

    def delete_bot(self, container_id):
        try:
            container = self.get_container(container_id)
            if container:
                container.remove(force=True)
                print(f"🗑️ Container deleted: {container_id}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error deleting container: {str(e)}")
            return False

    def get_logs(self, container_id):
        try:
            container = self.get_container(container_id)
            if container:
                return container.logs(tail=100).decode('utf-8').splitlines()
            return ["Container not found"]
        except Exception as e:
            return [f"Error fetching logs: {str(e)}"]

    def get_container_status(self, container_id):
        """Get real container status from Docker"""
        try:
            container = self.get_container(container_id)
            if container:
                container.reload()  # Refresh container data
                status = container.status
                # Map Docker status to our status
                status_map = {
                    'running': 'running',
                    'exited': 'stopped',
                    'created': 'stopped',
                    'restarting': 'running',
                    'paused': 'stopped',
                    'dead': 'error'
                }
                return status_map.get(status, 'error')
            return 'error'
        except Exception as e:
            print(f"❌ Error getting container status: {str(e)}")
            return 'error'


# -------------------------------------------------------------------
# Mock Docker Manager (for dev / Windows without Docker)
# -------------------------------------------------------------------
class MockDockerManager(DockerManagerBase):
    """Simulates Docker container behavior"""

    def __init__(self):
        super().__init__()
        print("🔧 Using Mock Docker Manager (Development Mode)")

    def create_bot_container(self, user, bot_config):
        container_id = f"mock_{random.randint(1000000000, 9999999999)}"
        container_name = f"{user.username}_{user.id}_{bot_config.bot_name}"

        bot_info = {
            "bot_type": bot_config.bot_type,
            "bot_name": bot_config.bot_name,
            "symbol": bot_config.symbol,
            "timeframe": bot_config.timeframe,
            "timeframe_type": getattr(bot_config, 'timeframe_type', 'm'),
            "lot_size": bot_config.lot_size,
            "delta_region": getattr(bot_config, 'delta_region', 'india'),
            "testnet": getattr(bot_config, 'testnet', False),
            "api_port": getattr(bot_config, 'api_port', 8080),
            "log_level": getattr(bot_config, 'log_level', 'INFO'),
            "log_file": getattr(bot_config, 'log_file', 'trading_bot.log'),
        }

        if bot_config.bot_type == "EMA":
            bot_info["ema_period"] = bot_config.ema_period
        elif bot_config.bot_type == "RSI_SMA":
            bot_info.update({
                "rsi_period": bot_config.rsi_period,
                "rsi_overbought": bot_config.rsi_overbought,
                "rsi_oversold": bot_config.rsi_oversold,
                "sma_period": bot_config.sma_period,
                "tv_symbol": getattr(bot_config, 'tv_symbol', 'BTCUSDT'),
                "use_tradingview_fallback": getattr(bot_config, 'use_tradingview_fallback', True)
            })

        self.containers[container_id] = {
            "status": "running",
            "name": container_name,
            "config": bot_info,
            "logs": [
                f"📦 Mock container {container_id} created",
                f"Bot Name: {bot_config.bot_name}",
                f"Bot Type: {bot_config.bot_type}",
                f"Symbol: {bot_config.symbol}",
                f"Timeframe: {bot_config.timeframe}{getattr(bot_config, 'timeframe_type', 'm')}",
                f"Lot Size: {bot_config.lot_size}",
                f"Testnet: {getattr(bot_config, 'testnet', False)}",
                f"Configuration: {bot_info}",
                "Mock trading started...",
                "Connecting to Delta Exchange...",
                f"Using Delta Region: {getattr(bot_config, 'delta_region', 'india')}",
                f"API Port: {getattr(bot_config, 'api_port', 8080)}",
                f"Log Level: {getattr(bot_config, 'log_level', 'INFO')}"
            ]
        }

        print(f"✅ Created mock container: {container_id} ({container_name})")
        return container_id, container_name

    def list_containers(self):
        return list(self.containers.keys())

    def get_container(self, container_id):
        return self.containers.get(container_id)

    def stream_logs(self, container_id):
        print(f"📋 [MOCK] Fetching logs for: {container_id}")

        if container_id not in self.containers:
            yield f"❌ Container {container_id} not found."
            return

        # First yield existing logs
        for log in self.containers[container_id]["logs"]:
            yield log

        # Then simulate new logs
        for i in range(1, 20):
            log = f"[{time.strftime('%H:%M:%S')}] Mock log line {i} - Bot is running..."
            self.containers[container_id]["logs"].append(log)
            yield log
            time.sleep(0.5)
        yield f"✅ Stream complete for {container_id}"

    def stop_bot(self, container_id):
        return self.stop_container(container_id)

    def stop_container(self, container_id):
        if container_id in self.containers:
            self.containers[container_id]["status"] = "stopped"
            self.containers[container_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Bot stopped by user")
            print(f"🛑 Mock container stopped: {container_id}")
            return True
        return False

    def start_bot(self, container_id):
        """Start a stopped mock container"""
        if container_id in self.containers:
            self.containers[container_id]["status"] = "running"
            self.containers[container_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Bot started by user")
            print(f"▶️ Mock container started: {container_id}")
            return True
        return False

    def delete_bot(self, container_id):
        if container_id in self.containers:
            del self.containers[container_id]
            print(f"🗑️ Mock container deleted: {container_id}")
            return True
        return False

    def get_logs(self, container_id):
        if container_id in self.containers:
            return self.containers[container_id]["logs"][-100:]  # Last 100 logs
        return ["Container not found"]

    def get_container_status(self, container_id):
        """Get mock container status"""
        if container_id in self.containers:
            return self.containers[container_id]["status"]
        return 'error'


# -------------------------------------------------------------------
# Safe Docker Initialization (Auto-detects OS and Docker status)
# -------------------------------------------------------------------
def get_docker_manager():
    try:
        system = platform.system().lower()

        if "DOCKER_HOST" not in os.environ:
            if system == "windows":
                os.environ["DOCKER_HOST"] = "npipe:////./pipe/docker_engine"
            else:
                os.environ["DOCKER_HOST"] = "unix:///var/run/docker.sock"

        client = docker.from_env()
        client.ping()  # verify connection
        print("🐳 Connected to Docker successfully!")
        return RealDockerManager()

    except DockerException as e:
        print(f"⚠️ Docker not available: {e}")
        print("🔧 Switching to Mock Docker Manager...")
        return MockDockerManager()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("🔧 Using Mock Docker Manager as fallback.")
        return MockDockerManager()


# -------------------------------------------------------------------
# Singleton Instance
# -------------------------------------------------------------------
# Use auto-detection for better compatibility
docker_manager = get_docker_manager()
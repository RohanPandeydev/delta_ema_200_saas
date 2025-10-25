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
                "BOT_TYPE": bot_config.bot_type,
                "SYMBOL": bot_config.symbol,
                "LOT_SIZE": str(getattr(bot_config, 'lot_size', '3.0')),
                "DELTA_API_KEY": bot_config.delta_api_key,
                "DELTA_API_SECRET": bot_config.delta_api_secret,
                "DELTA_REGION": "india",
                "USE_TESTNET": "False",
                "CONTAINER_ID": container_name,
            }

            # Bot type specific configs
            if bot_config.bot_type == "EMA":
                environment.update({
                    "EMA_PERIOD": str(bot_config.ema_period),
                    "TIMEFRAME_1M": str(bot_config.timeframe)
                })
            elif bot_config.bot_type == "RSI_SMA":
                environment.update({
                    "RSI_PERIOD": str(bot_config.rsi_period),
                    "SMA_PERIOD": str(bot_config.sma_period),
                    "RSI_OVERBOUGHT": "70",
                    "RSI_OVERSOLD": "30",
                    "TIMEFRAME_1M": str(bot_config.timeframe),
                    "TIMEFRAME_CANDLE_M": str(getattr(bot_config, 'timeframe_candle_m', '3'))
                })

            # Telegram setup
            if getattr(bot_config, 'telegram_bot_token', None) and getattr(bot_config, 'telegram_chat_id', None):
                environment.update({
                    "TELEGRAM_BOT_TOKEN": bot_config.telegram_bot_token,
                    "TELEGRAM_CHAT_ID": bot_config.telegram_chat_id
                })

            # Create container
            container = self.client.containers.run(
                "trading-bot:latest",
                name=container_name,
                environment=environment,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )

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
                for log in container.logs(tail=50).decode('utf-8').splitlines():
                    yield log
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
        except:
            return False

    def delete_bot(self, container_id):
        try:
            container = self.get_container(container_id)
            if container:
                container.remove(force=True)
                print(f"🗑️ Container deleted: {container_id}")
                return True
            return False
        except:
            return False

    def get_logs(self, container_id):
        try:
            container = self.get_container(container_id)
            if container:
                return container.logs(tail=100).decode('utf-8').splitlines()
            return ["Container not found"]
        except:
            return ["Error fetching logs"]


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
            "symbol": bot_config.symbol,
            "timeframe": getattr(bot_config, 'timeframe', '15'),
        }

        if bot_config.bot_type == "EMA":
            bot_info["ema_period"] = getattr(bot_config, 'ema_period', '200')
        elif bot_config.bot_type == "RSI_SMA":
            bot_info.update({
                "rsi_period": getattr(bot_config, 'rsi_period', '14'),
                "sma_period": getattr(bot_config, 'sma_period', '21')
            })

        self.containers[container_id] = {
            "status": "running",
            "name": container_name,
            "config": bot_info,
            "logs": [
                f"📦 Mock container {container_id} created",
                f"Bot Type: {bot_config.bot_type}",
                f"Symbol: {bot_config.symbol}",
                f"Configuration: {bot_info}",
                "Mock trading started...",
                "Connecting to Delta Exchange..."
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
        print(f"📊 [MOCK] Available containers: {self.list_containers()}")

        if container_id not in self.containers:
            yield f"❌ Container {container_id} not found."
            return

        for i in range(1, 20):
            log = f"[{time.strftime('%H:%M:%S')}] Log line {i} from {container_id}"
            self.containers[container_id]["logs"].append(log)
            yield log
            time.sleep(0.5)
        yield f"✅ Stream complete for {container_id}"

    def stop_bot(self, container_id):
        return self.stop_container(container_id)

    def stop_container(self, container_id):
        if container_id in self.containers:
            self.containers[container_id]["status"] = "stopped"
            print(f"🛑 Mock container stopped: {container_id}")
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
            return self.containers[container_id]["logs"]
        return ["Container not found"]


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
# Force using real Docker manager
docker_manager = RealDockerManager()

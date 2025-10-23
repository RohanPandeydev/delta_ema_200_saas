import docker
from datetime import datetime
from models import db, BotContainer, Credential
from cryptography.fernet import Fernet
import os

class DockerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.network = os.getenv('DOCKER_NETWORK', 'trading_bot_network')
        self.image = os.getenv('BOT_IMAGE', 'trading-bot:latest')
        
        # Encryption
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            print(f"⚠️ Generated encryption key: {key.decode()}")
            print("⚠️ Set ENCRYPTION_KEY in .env file!")
        
        if isinstance(key, str):
            key = key.encode()
        self.cipher = Fernet(key)
    
    def encrypt(self, text):
        """Encrypt text"""
        if not text:
            return None
        return self.cipher.encrypt(text.encode()).decode()
    
    def decrypt(self, encrypted):
        """Decrypt text"""
        if not encrypted:
            return ""
        return self.cipher.decrypt(encrypted.encode()).decode()
    
    def spawn_container(self, user_id, credential_id):
        """Spawn a new bot container for user"""
        try:
            # Get credential
            cred = Credential.query.get(credential_id)
            if not cred or cred.user_id != user_id:
                return {'success': False, 'error': 'Invalid credential'}
            
            # Check if already running
            existing = BotContainer.query.filter_by(
                user_id=user_id,
                credential_id=credential_id,
                status='running'
            ).first()
            
            if existing:
                return {'success': False, 'error': 'Bot already running for this credential'}
            
            # Decrypt credentials
            api_key = self.decrypt(cred.api_key_encrypted)
            api_secret = self.decrypt(cred.api_secret_encrypted)
            telegram_token = self.decrypt(cred.telegram_token_encrypted) if cred.telegram_token_encrypted else ""
            
            # Container name
            container_name = f"bot_user{user_id}_cred{credential_id}_{int(datetime.utcnow().timestamp())}"
            
            # Environment variables for YOUR bot
            environment = {
                'DELTA_API_KEY': api_key,
                'DELTA_API_SECRET': api_secret,
                'SYMBOL': cred.symbol,
                'LOT_SIZE': str(cred.lot_size),
                'TIMEFRAME_1M': str(cred.timeframe),
                'DELTA_REGION': cred.delta_region,
                'TESTNET': str(cred.testnet),
                'TELEGRAM_BOT_TOKEN': telegram_token,
                'TELEGRAM_CHAT_ID': cred.telegram_chat_id or '',
                'LOG_LEVEL': 'INFO',
                'LOG_FILE': 'trading_bot.log'
            }
            
            print(f"🐳 Spawning container: {container_name}")
            print(f"📊 Config: {cred.symbol} | {cred.lot_size} | {cred.timeframe}m")
            
            # Create container
            container = self.client.containers.run(
                self.image,
                name=container_name,
                environment=environment,
                detach=True,
                restart_policy={'Name': 'unless-stopped'},
                mem_limit='512m',
                network=self.network,
                labels={
                    'user_id': str(user_id),
                    'credential_id': str(credential_id),
                    'managed_by': 'orchestrator'
                }
            )
            
            # Save to database
            bot_container = BotContainer(
                user_id=user_id,
                credential_id=credential_id,
                container_id=container.id,
                container_name=container_name,
                status='running',
                started_at=datetime.utcnow()
            )
            db.session.add(bot_container)
            db.session.commit()
            
            print(f"✅ Container spawned: {container.id[:12]}")
            
            return {
                'success': True,
                'container_id': container.id,
                'container_name': container_name
            }
            
        except Exception as e:
            print(f"❌ Error spawning container: {e}")
            return {'success': False, 'error': str(e)}
    
    def stop_container(self, container_id):
        """Stop and remove container"""
        try:
            bot = BotContainer.query.filter_by(container_id=container_id).first()
            if not bot:
                return {'success': False, 'error': 'Container not found'}
            
            # Stop Docker container
            try:
                container = self.client.containers.get(container_id)
                container.stop(timeout=10)
                container.remove()
            except docker.errors.NotFound:
                pass
            
            # Update database
            bot.status = 'stopped'
            bot.stopped_at = datetime.utcnow()
            db.session.commit()
            
            print(f"✅ Container stopped: {container_id[:12]}")
            return {'success': True}
            
        except Exception as e:
            print(f"❌ Error stopping container: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_logs(self, container_id, tail=50):
        """Get container logs"""
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
            return logs.split('\n')
        except Exception as e:
            return [f"Error: {str(e)}"]
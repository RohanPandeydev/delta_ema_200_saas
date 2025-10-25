# ============================================
# FILE: orchestrator/services/docker_manager.py
# ============================================
"""
Docker container management service
"""
import docker
import threading
import time
from datetime import datetime
from orchestrator.extensions import db, socketio
from orchestrator.models import BotContainer, Credential, User
from orchestrator.services.encryption import encryption_service

class DockerManager:
    """Manage Docker containers for trading bots"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.network = 'trading_bot_network'
        self.image = 'trading-bot:latest'
    
    def spawn_user_container(self, user_id, credential_id):
        """
        Create and start a new trading bot container for a user
        
        Args:
            user_id: User ID
            credential_id: Credential ID to use
            
        Returns:
            dict: Container info or error
        """
        try:
            # Get credential
            credential = Credential.query.get(credential_id)
            if not credential or credential.user_id != user_id:
                return {'success': False, 'error': 'Invalid credential'}
            
            # Check if container already exists
            existing = BotContainer.query.filter_by(
                user_id=user_id,
                credential_id=credential_id,
                status='running'
            ).first()
            
            if existing:
                return {'success': False, 'error': 'Container already running'}
            
            # Decrypt credentials
            api_key = encryption_service.decrypt(credential.api_key_encrypted)
            api_secret = encryption_service.decrypt(credential.api_secret_encrypted)
            telegram_token = encryption_service.decrypt(credential.telegram_token_encrypted) if credential.telegram_token_encrypted else ""
            
            # Create container name
            container_name = f"bot_user{user_id}_cred{credential_id}_{int(datetime.utcnow().timestamp())}"
            
            # Environment variables for bot
            environment = {
                'USER_ID': str(user_id),
                'CREDENTIAL_ID': str(credential_id),
                'DELTA_API_KEY': api_key,
                'DELTA_API_SECRET': api_secret,
                'SYMBOL': credential.symbol,
                'LOT_SIZE': str(credential.lot_size),
                'TIMEFRAME_1M': str(credential.timeframe),
                'TELEGRAM_BOT_TOKEN': telegram_token,
                'TELEGRAM_CHAT_ID': credential.telegram_chat_id or '',
                'TESTNET': 'False',
                'DELTA_REGION': 'india'
            }
            
            # Create container
            container = self.client.containers.run(
                self.image,
                name=container_name,
                environment=environment,
                detach=True,
                restart_policy={'Name': 'always'},
                mem_limit='512m',
                cpu_quota=50000,
                network=self.network,
                labels={
                    'user_id': str(user_id),
                    'credential_id': str(credential_id),
                    'managed_by': 'orchestrator'
                }
            )

            # Start background log streaming for this container
            try:
                self.start_log_stream_for_container(container.id)
            except Exception:
                pass
            
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
            
            return {
                'success': True,
                'container_id': container.id,
                'container_name': container_name
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def stop_user_container(self, container_id):
        """
        Stop and remove a user's container
        
        Args:
            container_id: Docker container ID
            
        Returns:
            dict: Success status
        """
        try:
            # Get container from database
            bot_container = BotContainer.query.filter_by(container_id=container_id).first()
            
            if not bot_container:
                return {'success': False, 'error': 'Container not found in database'}
            
            # Stop Docker container
            try:
                container = self.client.containers.get(container_id)
                container.stop(timeout=10)
                container.remove()
            except docker.errors.NotFound:
                pass  # Container already removed
            
            # Update database
            bot_container.status = 'stopped'
            bot_container.stopped_at = datetime.utcnow()
            db.session.commit()
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_container_logs(self, container_id, tail=20):
        """
        Get container logs
        
        Args:
            container_id: Docker container ID
            tail: Number of lines to retrieve
            
        Returns:
            list: Log lines
        """
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
            return logs.split('\n')
        except Exception as e:
            return [f"Error fetching logs: {str(e)}"]
    
    def get_container_stats(self, container_id):
        """Get container resource stats"""
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            return stats
        except:
            return None

    def _log_stream_worker(self, container_id):
        """Background worker that streams container logs and emits via SocketIO."""
        room = f"logs_{container_id}"
        try:
            container = self.client.containers.get(container_id)
        except Exception as e:
            # Container might have been removed
            return

        try:
            # Stream logs (follow=True) and emit lines to the room
            for raw in container.logs(stream=True, follow=True, tail=10):
                try:
                    if not raw:
                        continue
                    # raw may be bytes
                    line = raw.decode('utf-8', errors='replace').rstrip('\n')
                    socketio.emit('log_update', {'container_id': container_id, 'log': line}, room=room)
                except Exception:
                    # Avoid crashing the thread on single-line errors
                    continue
                # small sleep to yield
                time.sleep(0.01)
        except Exception:
            # If streaming fails, just exit the worker
            return

    def start_log_stream_for_container(self, container_id):
        """Start a daemon thread to stream logs for a specific container id.

        Safe to call multiple times; starts a new thread per call.
        """
        t = threading.Thread(target=self._log_stream_worker, args=(container_id,))
        t.daemon = True
        t.start()

# Global instance
docker_manager = DockerManager()
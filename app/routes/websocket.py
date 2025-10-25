from flask import Blueprint, request
from flask_login import current_user, login_required
from flask_socketio import emit
from app.models.bot import BotConfiguration

# Import socketio from app factory
from app import socketio

websocket_bp = Blueprint('websocket', __name__)

# Store active log streams
active_log_streams = {}

@socketio.on('connect')
@login_required
def handle_connect():
    """Handle WebSocket connection"""
    emit('connected', {'data': f'Connected as {current_user.username}'})

@socketio.on('start_log_stream')
@login_required  
def handle_start_log_stream(data):
    """Start streaming logs for a bot via WebSocket"""
    from app.utils.docker_manager import docker_manager
    
    bot_id = data['bot_id']
    
    # Verify user owns this bot
    bot = BotConfiguration.query.get(bot_id)
    if not bot or bot.user_id != current_user.id:
        emit('error', {'message': 'Unauthorized'})
        return
    
    # Stop any existing stream for this bot
    if bot_id in active_log_streams:
        active_log_streams[bot_id] = False
    
    # Start new log stream
    active_log_streams[bot_id] = True
    
    def stream_logs():
        """Background task to stream logs"""
        try:
            for log_line in docker_manager.stream_logs(bot.container_id):
                if not active_log_streams.get(bot_id, False):
                    break  # Stop if stream was cancelled
                emit('log_update', {
                    'bot_id': bot_id,
                    'log_line': log_line
                }, room=request.sid)
        except Exception as e:
            emit('error', {
                'bot_id': bot_id,
                'message': f'Log stream error: {str(e)}'
            }, room=request.sid)
    
    # Start streaming in background
    socketio.start_background_task(stream_logs)
    emit('stream_started', {'bot_id': bot_id})

@socketio.on('stop_log_stream')
@login_required
def handle_stop_log_stream(data):
    """Stop streaming logs for a bot"""
    bot_id = data['bot_id']
    active_log_streams[bot_id] = False
    emit('stream_stopped', {'bot_id': bot_id})

@socketio.on('disconnect')
def handle_disconnect():
    """Stop all streams when user disconnects"""
    # Stop all active streams for this connection
    for bot_id in list(active_log_streams.keys()):
        active_log_streams[bot_id] = False
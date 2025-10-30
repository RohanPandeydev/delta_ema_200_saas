from flask import Blueprint, request
from flask_login import current_user, login_required
from flask_socketio import emit
from app.models.bot import BotConfiguration

# Import socketio from app factory
from app import socketio, db

websocket_bp = Blueprint('websocket', __name__)

# Store active log streams
active_log_streams = {}

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    if current_user.is_authenticated:
        emit('connected', {'data': f'Connected as {current_user.username}', 'user_id': current_user.id})
    else:
        emit('error', {'message': 'Authentication required'})

@socketio.on('start_log_stream')
@login_required  
def handle_start_log_stream(data):
    """Start streaming logs for a bot via WebSocket"""
    from app.utils.docker_manager import docker_manager
    
    bot_id = data.get('bot_id')
    if not bot_id:
        emit('error', {'message': 'Bot ID is required'})
        return
    
    try:
        # Verify user owns this bot
        bot = BotConfiguration.query.get(bot_id)
        if not bot or bot.user_id != current_user.id:
            emit('error', {'message': 'Unauthorized access to bot logs'})
            return
        
        # Check if bot has a container
        if not bot.container_id:
            emit('error', {'message': 'Bot container not found'})
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
                    
                    # Emit log line to specific client
                    emit('log_update', {
                        'bot_id': bot_id,
                        'bot_name': bot.bot_name,
                        'log_line': log_line,
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=request.sid)
                    
            except Exception as e:
                emit('error', {
                    'bot_id': bot_id,
                    'message': f'Log stream error: {str(e)}'
                }, room=request.sid)
        
        # Start streaming in background
        socketio.start_background_task(stream_logs)
        emit('stream_started', {
            'bot_id': bot_id,
            'bot_name': bot.bot_name,
            'message': 'Log stream started'
        })
        
    except Exception as e:
        emit('error', {'message': f'Error starting log stream: {str(e)}'})

@socketio.on('stop_log_stream')
@login_required
def handle_stop_log_stream(data):
    """Stop streaming logs for a bot"""
    bot_id = data.get('bot_id')
    if bot_id in active_log_streams:
        active_log_streams[bot_id] = False
        emit('stream_stopped', {
            'bot_id': bot_id,
            'message': 'Log stream stopped'
        })
    else:
        emit('error', {'message': 'No active log stream found for this bot'})

@socketio.on('get_bot_status')
@login_required
def handle_get_bot_status(data):
    """Get real-time status update for a bot"""
    from app.utils.docker_manager import docker_manager
    
    bot_id = data.get('bot_id')
    if not bot_id:
        emit('error', {'message': 'Bot ID is required'})
        return
    
    try:
        bot = BotConfiguration.query.get(bot_id)
        if not bot or bot.user_id != current_user.id:
            emit('error', {'message': 'Unauthorized access'})
            return
        
        # Get real-time status from Docker
        docker_status = docker_manager.get_container_status(bot.container_id)
        
        # Update database if status changed
        if docker_status and docker_status != bot.status:
            bot.status = docker_status
            db.session.commit()
        
        emit('bot_status_update', {
            'bot_id': bot_id,
            'bot_name': bot.bot_name,
            'status': docker_status or bot.status,
            'container_id': bot.container_id
        })
        
    except Exception as e:
        emit('error', {'message': f'Error getting bot status: {str(e)}'})

@socketio.on('subscribe_bot_updates')
@login_required
def handle_subscribe_bot_updates(data):
    """Subscribe to real-time updates for a bot"""
    bot_id = data.get('bot_id')
    if not bot_id:
        emit('error', {'message': 'Bot ID is required'})
        return
    
    try:
        bot = BotConfiguration.query.get(bot_id)
        if not bot or bot.user_id != current_user.id:
            emit('error', {'message': 'Unauthorized access'})
            return
        
        # Join room for this bot (room name format: bot_{bot_id})
        socketio.join_room(f'bot_{bot_id}', sid=request.sid)
        emit('subscribed', {
            'bot_id': bot_id,
            'bot_name': bot.bot_name,
            'message': 'Subscribed to bot updates'
        })
        
    except Exception as e:
        emit('error', {'message': f'Error subscribing to bot updates: {str(e)}'})

@socketio.on('unsubscribe_bot_updates')
@login_required
def handle_unsubscribe_bot_updates(data):
    """Unsubscribe from bot updates"""
    bot_id = data.get('bot_id')
    if bot_id:
        socketio.leave_room(f'bot_{bot_id}', sid=request.sid)
        emit('unsubscribed', {
            'bot_id': bot_id,
            'message': 'Unsubscribed from bot updates'
        })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnect - clean up resources"""
    # Stop all active streams for this connection
    user_streams = [bot_id for bot_id, active in active_log_streams.items() 
                   if active and BotConfiguration.query.get(bot_id).user_id == current_user.id]
    
    for bot_id in user_streams:
        active_log_streams[bot_id] = False
    
    # Leave all bot rooms
    if current_user.is_authenticated:
        user_bots = BotConfiguration.query.filter_by(user_id=current_user.id).all()
        for bot in user_bots:
            socketio.leave_room(f'bot_{bot.id}', sid=request.sid)
    
    emit('disconnected', {'message': 'Disconnected from WebSocket'})

# Utility function to broadcast bot status updates to all subscribed clients
def broadcast_bot_status(bot_id, status):
    """Broadcast bot status update to all subscribed clients"""
    socketio.emit('bot_status_update', {
        'bot_id': bot_id,
        'status': status,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f'bot_{bot_id}')

# Utility function to broadcast bot logs to all subscribed clients  
def broadcast_bot_log(bot_id, log_line):
    """Broadcast bot log to all subscribed clients"""
    socketio.emit('bot_log_broadcast', {
        'bot_id': bot_id,
        'log_line': log_line,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f'bot_{bot_id}')
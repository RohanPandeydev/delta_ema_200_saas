from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.models.bot import BotConfiguration

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    try:
        user_bots = BotConfiguration.query.filter_by(user_id=current_user.id).all()
        bots = list(user_bots) if user_bots else []
        
        # Prepare bot data for template with enhanced information
        enhanced_bots = []
        for bot in bots:
            enhanced_bots.append({
                'id': bot.id,
                'bot_name': bot.bot_name,
                'bot_type': bot.bot_type,
                'status': bot.status,
                'container_name': bot.container_name,
                'symbol': bot.symbol,
                'timeframe': bot.timeframe,
                'timeframe_type': bot.timeframe_type,
                'lot_size': bot.lot_size,
                'created_at': bot.created_at,
                'testnet': bot.testnet,
                # Bot-specific configurations for display
                'ema_period': getattr(bot, 'ema_period', None),
                'rsi_period': getattr(bot, 'rsi_period', None),
                'sma_period': getattr(bot, 'sma_period', None)
            })
        
    except Exception as e:
        print(f"Error fetching bots: {e}")
        enhanced_bots = []
    
    return render_template('dashboard/index.html', bots=enhanced_bots)

@dashboard_bp.route('/debug/bots')
@login_required
def debug_bots():
    """Debug route to check bot data"""
    try:
        user_bots = BotConfiguration.query.filter_by(user_id=current_user.id).all()
        bot_data = []
        for bot in user_bots:
            bot_data.append({
                'id': bot.id,
                'name': bot.bot_name,
                'type': bot.bot_type,
                'status': bot.status,
                'container': bot.container_name,
                'symbol': bot.symbol,
                'timeframe': f"{bot.timeframe}{bot.timeframe_type}",
                'lot_size': bot.lot_size,
                'testnet': bot.testnet,
                'ema_period': getattr(bot, 'ema_period', 'N/A'),
                'rsi_period': getattr(bot, 'rsi_period', 'N/A'),
                'sma_period': getattr(bot, 'sma_period', 'N/A'),
                'created_at': bot.created_at.strftime('%Y-%m-%d %H:%M:%S') if bot.created_at else 'N/A'
            })
        
        return jsonify({
            'user_id': current_user.id,
            'username': current_user.username,
            'is_premium': current_user.is_premium,
            'bot_count': len(user_bots),
            'bots': bot_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/bot/<int:bot_id>/details')
@login_required
def bot_details(bot_id):
    """Get detailed information about a specific bot"""
    try:
        bot = BotConfiguration.query.filter_by(
            id=bot_id, 
            user_id=current_user.id
        ).first_or_404()
        
        bot_details = {
            'id': bot.id,
            'bot_name': bot.bot_name,
            'bot_type': bot.bot_type,
            'status': bot.status,
            'container_id': bot.container_id,
            'container_name': bot.container_name,
            
            # Trading Configuration
            'symbol': bot.symbol,
            'lot_size': bot.lot_size,
            'timeframe': f"{bot.timeframe}{bot.timeframe_type}",
            'testnet': bot.testnet,
            
            # Bot Specific Configuration
            'ema_period': getattr(bot, 'ema_period', None),
            'rsi_period': getattr(bot, 'rsi_period', None),
            'rsi_overbought': getattr(bot, 'rsi_overbought', None),
            'rsi_oversold': getattr(bot, 'rsi_oversold', None),
            'sma_period': getattr(bot, 'sma_period', None),
            'tv_symbol': getattr(bot, 'tv_symbol', None),
            'use_tradingview_fallback': getattr(bot, 'use_tradingview_fallback', None),
            
            # Timestamps
            'created_at': bot.created_at.strftime('%Y-%m-%d %H:%M:%S') if bot.created_at else 'N/A',
            'updated_at': bot.updated_at.strftime('%Y-%m-%d %H:%M:%S') if bot.updated_at else 'N/A'
        }
        
        return jsonify({
            'success': True,
            'bot': bot_details
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error fetching bot details: {str(e)}'
        }), 500

# WebSocket events will be added separately to avoid circular imports